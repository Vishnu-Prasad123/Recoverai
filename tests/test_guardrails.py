import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryDecision, RecoveryAction
from app.schemas.guardrail import GuardrailResult, GuardrailStatus
from guardrails.engine import guardrail_engine, GuardrailEngine
from guardrails.config import GuardrailConfig

client = TestClient(app)

def create_sample_feature(
    payment_id="pay_test_guard_001",
    amount=5000.0,
    failure_reason="temporary_bank_error",
    payment_method="upi",
    prev_attempts=1,
    prev_recovery_attempts=0,
    time_since_failure_minutes=30.0,
    status="FAILED"
) -> PaymentFeatureInputs:
    feat = PaymentFeatureInputs(
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
        customer_success_rate=0.85,
        customer_lifetime_value=25000.0,
        customer_previous_payments=12,
        status=status
    )
    return feat

def create_sample_decision(
    payment_id="pay_test_guard_001",
    action=RecoveryAction.RETRY,
    ev=3500.0,
    delay=0
) -> RecoveryDecision:
    return RecoveryDecision(
        payment_id=payment_id,
        action=action,
        confidence=0.88,
        rationale="Retry transient failure",
        expected_recovery_value=ev,
        priority="HIGH",
        recommended_delay_minutes=delay,
        risk_level="LOW"
    )

def test_valid_retry_allow():
    feat = create_sample_feature()
    dec = create_sample_decision()
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.ALLOW
    assert res.final_action == RecoveryAction.RETRY
    assert len(res.rules_triggered) == 0

def test_retry_at_max_attempts_block():
    feat = create_sample_feature(prev_recovery_attempts=2)
    dec = create_sample_decision()
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.BLOCK
    assert "MAX_RECOVERY_ATTEMPTS" in res.rules_triggered
    assert res.final_action == RecoveryAction.STOP

def test_excessive_customer_contacts_block():
    feat = create_sample_feature(prev_recovery_attempts=2)
    dec = create_sample_decision(action=RecoveryAction.PAYMENT_LINK)
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.BLOCK
    assert "MAX_CUSTOMER_CONTACTS" in res.rules_triggered

def test_high_value_payment_modify():
    feat = create_sample_feature(amount=35000.0)
    dec = create_sample_decision(action=RecoveryAction.PAYMENT_LINK, ev=24500.0)
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.MODIFY
    assert "HIGH_VALUE_REVIEW" in res.rules_triggered
    assert res.final_action == RecoveryAction.HUMAN_REVIEW
    assert res.requires_human_review is True

def test_already_recovered_operational_state_block():
    feat = create_sample_feature(status="RECOVERED")
    dec = create_sample_decision()
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.BLOCK
    assert "INVALID_PAYMENT_STATE" in res.rules_triggered

def test_cancelled_operational_state_block():
    feat = create_sample_feature(status="CANCELLED")
    dec = create_sample_decision()
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.BLOCK
    assert "INVALID_PAYMENT_STATE" in res.rules_triggered

def test_velocity_protection_block():
    feat = create_sample_feature(prev_recovery_attempts=1, time_since_failure_minutes=3.0)
    dec = create_sample_decision(action=RecoveryAction.RETRY)
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.BLOCK
    assert "VELOCITY_LIMIT" in res.rules_triggered

def test_low_expected_recovery_value_block():
    feat = create_sample_feature(amount=100.0)
    dec = create_sample_decision(action=RecoveryAction.RETRY, ev=50.0)
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.BLOCK
    assert "LOW_RECOVERY_POTENTIAL" in res.rules_triggered

def test_unreasonable_delay_modify():
    feat = create_sample_feature()
    dec = create_sample_decision(action=RecoveryAction.WAIT, delay=2880)  # 48 hours
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.MODIFY
    assert "UNREASONABLE_DELAY" in res.rules_triggered

def test_failsafe_fallback_on_corrupt_input():
    feat = create_sample_feature(amount=-500.0)
    dec = create_sample_decision()
    res = guardrail_engine.evaluate_decision(feat, dec)
    assert res.status == GuardrailStatus.BLOCK
    assert "FAIL_SAFE_FALLBACK" in res.rules_triggered

def test_ai_cannot_override_guardrails():
    """CRITICAL SECURITY TEST: AI claims 'Passed' and confidence 1.0, but guardrail blocks if rules fail."""
    feat = create_sample_feature(prev_recovery_attempts=2)  # Violates MAX_RECOVERY_ATTEMPTS
    ai_dec = RecoveryDecision(
        payment_id="pay_ai_override_test",
        action=RecoveryAction.RETRY,
        confidence=1.0,
        rationale="AI claims this is 100% safe",
        expected_recovery_value=5000.0,
        priority="HIGH",
        recommended_delay_minutes=0,
        risk_level="LOW",
        guardrail_notes="Passed"  # AI fake claim
    )
    res = guardrail_engine.evaluate_decision(feat, ai_dec)
    assert res.status == GuardrailStatus.BLOCK
    assert res.final_action == RecoveryAction.STOP
    assert "MAX_RECOVERY_ATTEMPTS" in res.rules_triggered

def test_ground_truth_fields_ignored():
    """Confirms ground-truth outcome fields are strictly absent from PaymentFeatureInputs schema."""
    feat = create_sample_feature()
    feat_fields = set(PaymentFeatureInputs.model_fields.keys())
    assert "recovered" not in feat_fields
    assert "amount_recovered" not in feat_fields
    assert "true_recovery_probability" not in feat_fields

def test_api_guardrail_evaluate_endpoint():
    res = client.post("/api/guardrails/evaluate", json={"payment_id": "pay_100001"})
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] in ["ALLOW", "MODIFY", "BLOCK"]
    assert "final_action" in data
    assert "rules_evaluated" in data

def test_audit_log_persisted_on_evaluation():
    res = client.post("/api/guardrails/evaluate", json={"payment_id": "pay_100001"})
    assert res.status_code == 200
    
    # Query database to confirm AuditLog record created
    from app.database import SessionLocal
    from app.models.audit import AuditLog
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.payment_id == "pay_100001").all()
        assert len(logs) > 0
        latest = logs[-1]
        assert "GUARDRAIL_" in latest.event_type
        assert latest.actor == "GUARDRAIL_ENGINE"
    finally:
        db.close()
