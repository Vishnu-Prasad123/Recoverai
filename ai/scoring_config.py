"""
RecoverAI - Recovery Scoring Engine Configuration
Defines scoring component weights, failure code base scores, method adjustments,
fatigue/decay constants, and priority classification thresholds.
"""

from typing import Dict
from dataclasses import dataclass, field

@dataclass
class ScoringConfig:
    # Component Weights (Must sum to 1.0)
    WEIGHT_FAILURE_REASON: float = 0.40
    WEIGHT_CUSTOMER_HISTORY: float = 0.30
    WEIGHT_ATTEMPT_FATIGUE: float = 0.15
    WEIGHT_TIME_DECAY: float = 0.15

    # Base Scores by Failure Reason (0 to 100)
    FAILURE_REASON_SCORES: Dict[str, float] = field(default_factory=lambda: {
        "network_failure": 85.0,
        "temporary_bank_error": 80.0,
        "authentication_failure": 75.0,
        "3ds_timeout": 70.0,
        "payment_method_issue": 50.0,
        "insufficient_funds": 35.0,
        "customer_abandonment": 20.0,
        "account_blocked": 5.0,
    })

    # Payment Method Adjustments (-10 to +10)
    PAYMENT_METHOD_ADJUSTMENTS: Dict[str, float] = field(default_factory=lambda: {
        "upi": 5.0,
        "wallet": 3.0,
        "card": 0.0,
        "netbanking": -3.0,
        "emi": -5.0,
    })

    # Attempt Fatigue Penalty (per prior recovery attempt)
    RECOVERY_ATTEMPT_PENALTY: float = 12.0  # -12 points per attempt
    PAYMENT_ATTEMPT_PENALTY: float = 6.0    # -6 points per attempt beyond 1

    # Time Decay (minutes)
    MAX_DECAY_MINUTES: float = 10080.0  # 7 days max window
    MAX_TIME_PENALTY: float = 25.0      # -25 points max time penalty

    # Probability Calibration Parameters (Calibrated Sigmoid Mapping)
    # Midpoint at 70.0 aligns mean predicted probability (~0.617) with dataset GT recovery rate (~0.604)
    SIGMOID_SLOPE: float = 0.075
    SIGMOID_MIDPOINT: float = 70.0
    MIN_PROBABILITY: float = 0.02
    MAX_PROBABILITY: float = 0.95

    # Priority Thresholds (Operational Distribution: ~30% HIGH, ~48% MEDIUM, ~22% LOW)
    HIGH_PRIORITY_MIN_EV: float = 2000.0
    HIGH_PRIORITY_MIN_PROB: float = 0.55
    HIGH_PRIORITY_PROB_OVERRIDE: float = 0.80

    MEDIUM_PRIORITY_MIN_EV: float = 500.0
    MEDIUM_PRIORITY_MIN_PROB: float = 0.35

SCORING_CONFIG = ScoringConfig()
