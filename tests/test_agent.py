import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryDecision, RecoveryAction
from ai.agent import ai_decision_agent, AIDecisionAgent
from ai.llm_provider import MockLLMProvider, RealLLMProvider

client = TestClient(app)

def create_sample_feature(
    payment_id="pay_test_agent_001",
    amount=5000.0,
    failure_reason="temporary_bank_error",
    payment_method="upi",
    success_rate=0.85,
    prev_attempts=1,
    prev_recovery_attempts=0,
    time_since_failure_minutes=30.0
) -> PaymentFeatureInputs:
    return PaymentFeatureInputs(
        payment_id=payment_id,
        customer_id="cust_test_101",
        amount=amount,
        currency="INR",
        payment_method=payment_method,
        failure_reason=failure_reason,
        timestamp=datetime.now(timezone.utc),
        previous_attempts=prev_attempts,
        previous_recovery_attempts=prev_recovery_attempts,
        time_since_failure_minutes=time_since_failure_minutes,
        customer_success_rate=success_rate,
        customer_lifetime_value=25000.0,
        customer_previous_payments=12,
    )

def test_decision_schema_valid_and_invalid_action():
    valid = RecoveryDecision(
        payment_id="p1",
        action=RecoveryAction.RETRY,
        confidence=0.9,
        rationale="Transient failure",
        expected_recovery_value=4000.0,
        priority="HIGH",
        recommended_delay_minutes=0,
        risk_level="LOW"
    )
    assert valid.action == "RETRY"

    with pytest.raises(ValueError):
        RecoveryDecision(
            payment_id="p1",
            action="INVALID_ACTION",  # Invalid action not in enum
            confidence=0.9,
            rationale="Test",
            expected_recovery_value=4000.0,
            priority="HIGH"
        )

def test_mock_provider_outputs():
    provider = MockLLMProvider()
    feat = create_sample_feature()
    from ai.scoring import scoring_engine
    score_res = scoring_engine.score_payment(feat)
    dec = provider.generate_decision(feat, score_res)
    assert isinstance(dec, RecoveryDecision)
    assert dec.action in [RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK, RecoveryAction.WAIT, RecoveryAction.STOP, RecoveryAction.HUMAN_REVIEW]

def test_real_provider_configuration_validation(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    real_p = RealLLMProvider()
    with pytest.raises(ValueError, match="LLM API Key missing"):
        real_p.validate_configuration()

def test_retry_scenario():
    feat = create_sample_feature(failure_reason="temporary_bank_error", prev_recovery_attempts=0)
    dec = ai_decision_agent.recommend_action(feat)
    assert dec.action == RecoveryAction.RETRY
    assert dec.confidence > 0.5
    assert len(dec.rationale) > 0

def test_payment_link_scenario():
    feat = create_sample_feature(failure_reason="insufficient_funds", prev_recovery_attempts=1)
    dec = ai_decision_agent.recommend_action(feat)
    assert dec.action == RecoveryAction.PAYMENT_LINK
    assert "Payment Link" in dec.rationale or "insufficient_funds" in dec.rationale

def test_wait_scenario():
    feat = create_sample_feature(failure_reason="network_failure", prev_recovery_attempts=0, time_since_failure_minutes=5.0)
    dec = ai_decision_agent.recommend_action(feat)
    assert dec.action == RecoveryAction.WAIT
    assert dec.recommended_delay_minutes > 0

def test_stop_scenario():
    feat = create_sample_feature(failure_reason="account_blocked")
    dec = ai_decision_agent.recommend_action(feat)
    assert dec.action == RecoveryAction.STOP
    assert "blocked" in dec.rationale.lower()

def test_human_review_scenario():
    feat = create_sample_feature(success_rate=0.10)
    dec = ai_decision_agent.recommend_action(feat)
    assert dec.action == RecoveryAction.HUMAN_REVIEW
    assert dec.risk_level in ["MEDIUM", "HIGH"]

def test_data_leakage_rejection():
    leaked_dict = {
        "payment_id": "pay_leak",
        "customer_id": "cust_leak",
        "amount": 5000.0,
        "payment_method": "upi",
        "failure_reason": "network_failure",
        "customer_success_rate": 0.8,
        "recovered": True  # FORBIDDEN
    }
    with pytest.raises(ValueError, match="DATA LEAKAGE DETECTED"):
        ai_decision_agent.recommend_action(leaked_dict)

def test_no_arbitrary_tool_execution():
    """Confirms AI Decision Agent has no execution or command capabilities."""
    agent_attrs = dir(ai_decision_agent)
    assert "execute_command" not in agent_attrs
    assert "run_shell" not in agent_attrs
    assert "charge_card" not in agent_attrs

def test_safe_fallback_on_exception():
    class ExceptionProvider:
        def generate_decision(self, features, score_result):
            raise RuntimeError("Simulated API exception")

    broken_agent = AIDecisionAgent(provider=ExceptionProvider())
    feat = create_sample_feature()
    dec = broken_agent.recommend_action(feat)
    assert dec.action == RecoveryAction.HUMAN_REVIEW
    assert dec.confidence == 0.0
    assert "Fallback" in dec.rationale

def test_api_decision_preview_endpoint():
    res = client.post("/api/decisions/preview", json={"payment_id": "pay_100001"})
    assert res.status_code == 200
    data = res.json()
    assert "action" in data
    assert data["action"] in ["RETRY", "PAYMENT_LINK", "WAIT", "STOP", "HUMAN_REVIEW"]
    assert "confidence" in data
    assert "rationale" in data

def test_api_batch_decision_preview_endpoint():
    res = client.post("/api/decisions/batch-preview", json={"payment_ids": ["pay_100001", "pay_100002"]})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["payment_id"] == "pay_100001"
    assert data[1]["payment_id"] == "pay_100002"
