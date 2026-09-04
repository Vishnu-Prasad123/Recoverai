"""
RecoverAI - Composable Guardrail Rule Hierarchy
Implements 100% deterministic safety rules enforcing hard limits, operational state
checks, high-value risk escalations, velocity protection, and fail-safe fallbacks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryDecision, RecoveryAction
from app.schemas.guardrail import GuardrailStatus, GuardrailRuleEvaluation
from guardrails.config import GUARDRAIL_CONFIG, GuardrailConfig

class BaseGuardrailRule(ABC):
    """Abstract base class for composable guardrail rules."""
    rule_id: str
    rule_name: str
    description: str

    @abstractmethod
    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        pass


class MaxRecoveryAttemptsRule(BaseGuardrailRule):
    rule_id = "MAX_RECOVERY_ATTEMPTS"
    rule_name = "Maximum Recovery Attempts Limit"
    description = "Blocks recovery actions if maximum prior recovery attempt threshold is reached."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        if decision.action in [RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK]:
            if features.previous_recovery_attempts >= config.MAX_RECOVERY_ATTEMPTS:
                return GuardrailRuleEvaluation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=GuardrailStatus.BLOCK,
                    severity="HIGH",
                    message=f"Blocked: Payment has reached the maximum of {features.previous_recovery_attempts} prior recovery attempts (Limit: {config.MAX_RECOVERY_ATTEMPTS})."
                )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Within maximum recovery attempt limit."
        )


class MaxCustomerContactsRule(BaseGuardrailRule):
    rule_id = "MAX_CUSTOMER_CONTACTS"
    rule_name = "Maximum Customer Contacts Limit"
    description = "Blocks direct customer contact (Payment Link) if contact attempt limit is reached."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        if decision.action == RecoveryAction.PAYMENT_LINK:
            if features.previous_recovery_attempts >= config.MAX_CUSTOMER_CONTACTS:
                return GuardrailRuleEvaluation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=GuardrailStatus.BLOCK,
                    severity="HIGH",
                    message=f"Blocked: Customer contact limit ({config.MAX_CUSTOMER_CONTACTS}) reached to prevent spam and customer friction."
                )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Within maximum customer contact limit."
        )


class HighValueProtectionRule(BaseGuardrailRule):
    rule_id = "HIGH_VALUE_REVIEW"
    rule_name = "High-Value Transaction Human Escalation"
    description = "Escalates high-value transactions to Human Review rather than automated execution."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        if features.amount >= config.HIGH_VALUE_THRESHOLD and decision.action in [RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK]:
            return GuardrailRuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                status=GuardrailStatus.MODIFY,
                severity="HIGH",
                message=f"Modified: Transaction amount (INR {features.amount:,.2f}) exceeds high-value threshold (INR {config.HIGH_VALUE_THRESHOLD:,.2f}). Human review required."
            )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Transaction amount is within standard automated limits."
        )


class PaymentOperationalStateRule(BaseGuardrailRule):
    rule_id = "INVALID_PAYMENT_STATE"
    rule_name = "Payment Operational State Eligibility"
    description = "Blocks recovery if payment is already recovered, cancelled, or expired."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        # Check operational status if present in dict or feature attributes
        current_status = getattr(features, "status", "FAILED")
        if current_status in config.FORBIDDEN_OPERATIONAL_STATES:
            return GuardrailRuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                status=GuardrailStatus.BLOCK,
                severity="CRITICAL",
                message=f"Blocked: Payment operational status is '{current_status}' and no longer eligible for recovery."
            )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Payment operational state is eligible for recovery."
        )


class VelocityProtectionRule(BaseGuardrailRule):
    rule_id = "VELOCITY_LIMIT"
    rule_name = "Rapid Attempt Velocity Limit"
    description = "Prevents gateway hammering by blocking retries initiated too quickly after a failure."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        if decision.action == RecoveryAction.RETRY and features.previous_recovery_attempts > 0:
            if features.time_since_failure_minutes < 10.0:  # < 10 minutes since last failure
                return GuardrailRuleEvaluation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=GuardrailStatus.BLOCK,
                    severity="MEDIUM",
                    message=f"Blocked: Action attempt too rapid ({features.time_since_failure_minutes:.1f} mins since failure). Enforcing velocity cooldown."
                )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Cooldown period satisfied."
        )


class LowRecoveryPotentialRule(BaseGuardrailRule):
    rule_id = "LOW_RECOVERY_POTENTIAL"
    rule_name = "Minimum Recovery Viability Check"
    description = "Blocks automated recovery if recovery probability or expected value is too low."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        ev = decision.expected_recovery_value
        if decision.action in [RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK]:
            if ev < config.MIN_EXPECTED_RECOVERY_VALUE:
                return GuardrailRuleEvaluation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=GuardrailStatus.BLOCK,
                    severity="MEDIUM",
                    message=f"Blocked: Expected Recovery Value (INR {ev:.2f}) is below minimum threshold (INR {config.MIN_EXPECTED_RECOVERY_VALUE:.2f})."
                )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Expected recovery value meets minimum economic viability."
        )


class UnreasonableDelayRule(BaseGuardrailRule):
    rule_id = "UNREASONABLE_DELAY"
    rule_name = "Maximum Wait Delay Validation"
    description = "Caps excessive wait delays to a maximum of 24 hours (1440 minutes)."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        if decision.action == RecoveryAction.WAIT:
            if decision.recommended_delay_minutes > config.MAX_RECOMMENDED_DELAY_MINUTES:
                return GuardrailRuleEvaluation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=GuardrailStatus.MODIFY,
                    severity="LOW",
                    message=f"Modified: Recommended delay ({decision.recommended_delay_minutes} mins) capped to maximum limit ({config.MAX_RECOMMENDED_DELAY_MINUTES} mins)."
                )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Delay duration is within reasonable parameters."
        )


class FailSafeFallbackRule(BaseGuardrailRule):
    rule_id = "FAIL_SAFE_FALLBACK"
    rule_name = "System Fail-Safe & Input Integrity"
    description = "Forces safe escalation to HUMAN_REVIEW or BLOCK if state or decision input is corrupt."

    def evaluate(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision,
        config: GuardrailConfig = GUARDRAIL_CONFIG
    ) -> GuardrailRuleEvaluation:
        if not features.payment_id or features.amount <= 0:
            return GuardrailRuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                status=GuardrailStatus.BLOCK,
                severity="CRITICAL",
                message="Blocked: Corrupt or missing payment feature state."
            )
        return GuardrailRuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=GuardrailStatus.ALLOW,
            severity="LOW",
            message="Passed: Input integrity verified."
        )
