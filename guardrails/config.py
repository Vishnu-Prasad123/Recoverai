"""
RecoverAI - Independent Guardrail Engine Configuration
Centralized configuration defining hard limits, thresholds, velocity windows,
and escalation parameters. Completely independent from AI models.
"""

from dataclasses import dataclass

@dataclass
class GuardrailConfig:
    # Hard Operational Limits
    MAX_RECOVERY_ATTEMPTS: int = 2          # Max gateway/recovery retries per payment
    MAX_CUSTOMER_CONTACTS: int = 2          # Max direct messages (Payment Link) per customer

    # High-Value Risk Controls
    HIGH_VALUE_THRESHOLD: float = 25000.0   # Payments >= INR 25,000 modify to HUMAN_REVIEW

    # Viability & Expected Value Thresholds
    MIN_RECOVERY_PROBABILITY: float = 0.15  # Block action if recovery probability < 15%
    MIN_EXPECTED_RECOVERY_VALUE: float = 100.0 # Block action if Expected Recovery Value < INR 100

    # Delay & Time Windows
    MAX_RECOMMENDED_DELAY_MINUTES: int = 1440 # 24 hours max wait delay
    VELOCITY_WINDOW_MINUTES: int = 60          # 60 mins velocity check window

    # Forbidden Operational States (Cannot recover if payment is already in these states)
    FORBIDDEN_OPERATIONAL_STATES: tuple = ("RECOVERED", "CANCELLED", "EXPIRED", "REFUNDED")

GUARDRAIL_CONFIG = GuardrailConfig()
