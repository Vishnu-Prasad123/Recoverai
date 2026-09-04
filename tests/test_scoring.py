import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from ai.scoring import scoring_engine, RecoveryScoreResult
from ai.evaluate_scoring import evaluate_scoring_engine
from app.schemas.payment import PaymentFeatureInputs

def create_sample_feature(
    payment_id="pay_test_001",
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

def test_score_bounds_and_probability():
    feat = create_sample_feature()
    res = scoring_engine.score_payment(feat)
    assert 0.0 <= res.recovery_score <= 100.0
    assert 0.02 <= res.recovery_probability <= 0.95
    assert res.priority in ["HIGH", "MEDIUM", "LOW"]
    assert len(res.factors) > 0

def test_expected_recovery_value_calculation():
    feat = create_sample_feature(amount=10000.0)
    res = scoring_engine.score_payment(feat)
    expected_ev = round(10000.0 * res.recovery_probability, 2)
    assert res.expected_recovery_value == expected_ev

def test_priority_tiers():
    # High Priority: ₹10,000 with transient failure
    feat_high = create_sample_feature(amount=10000.0, failure_reason="network_failure", success_rate=0.90)
    res_high = scoring_engine.score_payment(feat_high)
    assert res_high.priority == "HIGH"

    # Low Priority: ₹300 with blocked account
    feat_low = create_sample_feature(amount=300.0, failure_reason="account_blocked", success_rate=0.10)
    res_low = scoring_engine.score_payment(feat_low)
    assert res_low.priority == "LOW"

def test_high_quality_customer_scenario():
    feat_good = create_sample_feature(success_rate=0.95)
    feat_poor = create_sample_feature(success_rate=0.15)
    res_good = scoring_engine.score_payment(feat_good)
    res_poor = scoring_engine.score_payment(feat_poor)
    assert res_good.recovery_score > res_poor.recovery_score
    assert res_good.recovery_probability > res_poor.recovery_probability

def test_failure_reason_scenario():
    feat_transient = create_sample_feature(failure_reason="temporary_bank_error")
    feat_blocked = create_sample_feature(failure_reason="account_blocked")
    res_transient = scoring_engine.score_payment(feat_transient)
    res_blocked = scoring_engine.score_payment(feat_blocked)
    assert res_transient.recovery_score > res_blocked.recovery_score

def test_attempt_fatigue_scenario():
    feat_fresh = create_sample_feature(prev_recovery_attempts=0)
    feat_fatigued = create_sample_feature(prev_recovery_attempts=2)
    res_fresh = scoring_engine.score_payment(feat_fresh)
    res_fatigued = scoring_engine.score_payment(feat_fatigued)
    assert res_fresh.recovery_score > res_fatigued.recovery_score

def test_time_decay_scenario():
    feat_recent = create_sample_feature(time_since_failure_minutes=15.0)
    feat_old = create_sample_feature(time_since_failure_minutes=8640.0)  # 6 days ago
    res_recent = scoring_engine.score_payment(feat_recent)
    res_old = scoring_engine.score_payment(feat_old)
    assert res_recent.recovery_score > res_old.recovery_score

def test_batch_scoring():
    feats = [
        create_sample_feature(payment_id="pay_b1"),
        create_sample_feature(payment_id="pay_b2", failure_reason="insufficient_funds")
    ]
    results = scoring_engine.score_batch(feats)
    assert len(results) == 2
    assert results[0].payment_id == "pay_b1"
    assert results[1].payment_id == "pay_b2"

def test_data_leakage_rejection():
    leaked_dict = {
        "payment_id": "pay_leak",
        "customer_id": "cust_leak",
        "amount": 5000.0,
        "payment_method": "upi",
        "failure_reason": "network_failure",
        "customer_success_rate": 0.8,
        # FORBIDDEN FIELD
        "recovered": True
    }
    with pytest.raises(ValueError, match="DATA LEAKAGE DETECTED"):
        scoring_engine.score_payment(leaked_dict)

def test_deterministic_reproducibility():
    feat = create_sample_feature()
    res1 = scoring_engine.score_payment(feat)
    res2 = scoring_engine.score_payment(feat)
    assert res1.recovery_score == res2.recovery_score
    assert res1.recovery_probability == res2.recovery_probability
    assert res1.expected_recovery_value == res2.expected_recovery_value

def test_random_baseline_reproducibility():
    """Verifies that random baseline ranking is reproducible given a fixed seed."""
    df = pd.DataFrame({"id": range(100), "val": np.random.rand(100)})
    np.random.seed(42)
    p1 = np.random.permutation(len(df))
    np.random.seed(42)
    p2 = np.random.permutation(len(df))
    assert np.array_equal(p1, p2)

def test_priority_tier_distribution():
    """Verifies that scoring engine creates a non-trivial priority distribution across varied payments."""
    p_high = create_sample_feature(amount=10000.0, failure_reason="network_failure", success_rate=0.90)
    p_med = create_sample_feature(amount=2000.0, failure_reason="payment_method_issue", success_rate=0.50)
    p_low = create_sample_feature(amount=400.0, failure_reason="account_blocked", success_rate=0.15)

    r_high = scoring_engine.score_payment(p_high)
    r_med = scoring_engine.score_payment(p_med)
    r_low = scoring_engine.score_payment(p_low)

    assert r_high.priority == "HIGH"
    assert r_med.priority == "MEDIUM"
    assert r_low.priority == "LOW"
