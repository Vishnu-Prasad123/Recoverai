"""
RecoverAI - Core Recovery Scoring Engine
Calculates Recovery Score (0-100), Recovery Probability (0.0-1.0), Expected Recovery Value,
Priority Tier, and Explainable Factor list for merchant transparency.
Strictly enforces feature separation to prevent data leakage.
"""

import math
from typing import Dict, List, Any, Union
from pydantic import BaseModel, ConfigDict
from ai.scoring_config import SCORING_CONFIG, ScoringConfig
from app.schemas.payment import PaymentFeatureInputs

class FactorExplanation(BaseModel):
    factor: str
    impact: str  # positive, negative, neutral
    weight: float
    description: str

class RecoveryScoreResult(BaseModel):
    payment_id: str
    recovery_score: float  # 0.0 to 100.0
    recovery_probability: float  # 0.0 to 1.0
    expected_recovery_value: float  # amount * probability
    priority: str  # HIGH, MEDIUM, LOW
    factors: List[FactorExplanation]
    model_config = ConfigDict(from_attributes=True)

class RecoveryScoringEngine:
    def __init__(self, config: ScoringConfig = SCORING_CONFIG):
        self.config = config

    def _check_data_leakage(self, features_dict: Dict[str, Any]):
        """CRITICAL: Rejects input objects containing ground-truth evaluation labels."""
        forbidden_fields = {"recovered", "amount_recovered", "true_recovery_probability"}
        leaked = set(features_dict.keys()).intersection(forbidden_fields)
        if leaked:
            raise ValueError(
                f"DATA LEAKAGE DETECTED! Input feature set contains ground-truth evaluation labels: {leaked}. "
                "The scoring engine must ONLY evaluate pre-decision feature inputs."
            )

    def score_payment(self, features: Union[PaymentFeatureInputs, Dict[str, Any]]) -> RecoveryScoreResult:
        """
        Evaluates a single payment feature set using pre-decision features.
        Returns RecoveryScoreResult containing score, probability, expected value, priority, and explanations.
        """
        if isinstance(features, PaymentFeatureInputs):
            feat_dict = features.model_dump()
        elif isinstance(features, dict):
            feat_dict = features
        else:
            raise TypeError("features must be an instance of PaymentFeatureInputs or dict")

        # 1. Enforce Data Leakage Protection
        self._check_data_leakage(feat_dict)

        # Extract features
        payment_id = feat_dict["payment_id"]
        amount = float(feat_dict["amount"])
        failure_reason = str(feat_dict.get("failure_reason", "unknown")).lower()
        payment_method = str(feat_dict.get("payment_method", "upi")).lower()
        cust_success_rate = float(feat_dict.get("customer_success_rate", 0.5))
        prev_attempts = int(feat_dict.get("previous_attempts", 1))
        prev_recovery_attempts = int(feat_dict.get("previous_recovery_attempts", 0))
        minutes_ago = float(feat_dict.get("time_since_failure_minutes", 0.0))

        factors: List[FactorExplanation] = []

        # -------------------------------------------------------------
        # COMPONENT 1: Failure Reason & Payment Method Score
        # -------------------------------------------------------------
        base_failure_score = self.config.FAILURE_REASON_SCORES.get(failure_reason, 50.0)
        method_adj = self.config.PAYMENT_METHOD_ADJUSTMENTS.get(payment_method, 0.0)
        component_failure = max(0.0, min(100.0, base_failure_score + method_adj))

        if base_failure_score >= 70.0:
            factors.append(FactorExplanation(
                factor="failure_reason",
                impact="positive",
                weight=self.config.WEIGHT_FAILURE_REASON,
                description=f"Failure code '{failure_reason}' (via {payment_method.upper()}) is typically transient and has strong recovery potential."
            ))
        elif base_failure_score <= 35.0:
            factors.append(FactorExplanation(
                factor="failure_reason",
                impact="negative",
                weight=self.config.WEIGHT_FAILURE_REASON,
                description=f"Failure code '{failure_reason}' indicates severe structural or authorization blockage."
            ))
        else:
            factors.append(FactorExplanation(
                factor="failure_reason",
                impact="neutral",
                weight=self.config.WEIGHT_FAILURE_REASON,
                description=f"Failure code '{failure_reason}' has moderate recovery likelihood."
            ))

        # -------------------------------------------------------------
        # COMPONENT 2: Customer History Score
        # -------------------------------------------------------------
        component_customer = max(0.0, min(100.0, cust_success_rate * 100.0))

        if cust_success_rate >= 0.70:
            factors.append(FactorExplanation(
                factor="customer_history",
                impact="positive",
                weight=self.config.WEIGHT_CUSTOMER_HISTORY,
                description=f"Customer has a strong payment history ({cust_success_rate*100:.1f}% successful)."
            ))
        elif cust_success_rate <= 0.40:
            factors.append(FactorExplanation(
                factor="customer_history",
                impact="negative",
                weight=self.config.WEIGHT_CUSTOMER_HISTORY,
                description=f"Customer has a low historical payment success rate ({cust_success_rate*100:.1f}%)."
            ))

        # -------------------------------------------------------------
        # COMPONENT 3: Attempt Fatigue Penalty
        # -------------------------------------------------------------
        recovery_penalty = prev_recovery_attempts * self.config.RECOVERY_ATTEMPT_PENALTY
        payment_penalty = max(0, prev_attempts - 1) * self.config.PAYMENT_ATTEMPT_PENALTY
        total_attempt_penalty = recovery_penalty + payment_penalty
        component_attempts = max(0.0, 100.0 - total_attempt_penalty)

        if prev_recovery_attempts > 0:
            factors.append(FactorExplanation(
                factor="recovery_attempts",
                impact="negative",
                weight=self.config.WEIGHT_ATTEMPT_FATIGUE,
                description=f"Payment has already undergone {prev_recovery_attempts} prior recovery attempt(s), reducing success probability."
            ))

        # -------------------------------------------------------------
        # COMPONENT 4: Time Decay Penalty
        # -------------------------------------------------------------
        time_ratio = min(1.0, minutes_ago / self.config.MAX_DECAY_MINUTES)
        time_penalty = time_ratio * self.config.MAX_TIME_PENALTY
        component_time = max(0.0, 100.0 - time_penalty)

        if minutes_ago > 2880:  # > 2 days
            factors.append(FactorExplanation(
                factor="time_decay",
                impact="negative",
                weight=self.config.WEIGHT_TIME_DECAY,
                description=f"Payment failed {minutes_ago/1440:.1f} days ago; recovery potential degrades over time."
            ))

        # -------------------------------------------------------------
        # WEIGHTED AGGREGATION
        # -------------------------------------------------------------
        raw_score = (
            (component_failure * self.config.WEIGHT_FAILURE_REASON) +
            (component_customer * self.config.WEIGHT_CUSTOMER_HISTORY) +
            (component_attempts * self.config.WEIGHT_ATTEMPT_FATIGUE) +
            (component_time * self.config.WEIGHT_TIME_DECAY)
        )
        recovery_score = round(max(0.0, min(100.0, raw_score)), 2)

        # -------------------------------------------------------------
        # CALIBRATED PROBABILITY MAPPING (Sigmoid Curve)
        # -------------------------------------------------------------
        logit = self.config.SIGMOID_SLOPE * (recovery_score - self.config.SIGMOID_MIDPOINT)
        raw_prob = 1.0 / (1.0 + math.exp(-logit))
        recovery_probability = round(max(self.config.MIN_PROBABILITY, min(self.config.MAX_PROBABILITY, raw_prob)), 4)

        # Expected Recovery Value (Amount * Probability)
        expected_recovery_value = round(amount * recovery_probability, 2)

        # -------------------------------------------------------------
        # PRIORITY CLASSIFICATION
        # -------------------------------------------------------------
        if (expected_recovery_value >= self.config.HIGH_PRIORITY_MIN_EV and recovery_probability >= self.config.HIGH_PRIORITY_MIN_PROB) or (recovery_probability >= self.config.HIGH_PRIORITY_PROB_OVERRIDE):
            priority = "HIGH"
        elif expected_recovery_value >= self.config.MEDIUM_PRIORITY_MIN_EV and recovery_probability >= self.config.MEDIUM_PRIORITY_MIN_PROB:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        return RecoveryScoreResult(
            payment_id=payment_id,
            recovery_score=recovery_score,
            recovery_probability=recovery_probability,
            expected_recovery_value=expected_recovery_value,
            priority=priority,
            factors=factors
        )

    def score_batch(self, payments: List[Union[PaymentFeatureInputs, Dict[str, Any]]]) -> List[RecoveryScoreResult]:
        """Scores a batch of payment feature sets."""
        return [self.score_payment(p) for p in payments]

# Singleton Engine Instance
scoring_engine = RecoveryScoringEngine()
