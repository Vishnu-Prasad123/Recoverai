"""
RecoverAI - Core Guardrail Engine
Orchestrates composable safety rule evaluation, enforces deterministic action authority,
and generates standardized GuardrailResult responses.
100% independent from AI models.
"""

from typing import List, Dict, Any, Optional
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryDecision, RecoveryAction
from app.schemas.guardrail import GuardrailResult, GuardrailStatus, GuardrailRuleEvaluation
from guardrails.config import GUARDRAIL_CONFIG, GuardrailConfig
from guardrails.rules import (
    BaseGuardrailRule,
    MaxRecoveryAttemptsRule,
    MaxCustomerContactsRule,
    HighValueProtectionRule,
    PaymentOperationalStateRule,
    VelocityProtectionRule,
    LowRecoveryPotentialRule,
    UnreasonableDelayRule,
    FailSafeFallbackRule
)

class GuardrailEngine:
    """
    Independent Guardrail Safety Layer.
    Evaluates proposed AI decisions against deterministic business rules.
    """
    def __init__(self, config: GuardrailConfig = GUARDRAIL_CONFIG):
        self.config = config
        self.rules: List[BaseGuardrailRule] = [
            FailSafeFallbackRule(),
            PaymentOperationalStateRule(),
            MaxRecoveryAttemptsRule(),
            MaxCustomerContactsRule(),
            HighValueProtectionRule(),
            VelocityProtectionRule(),
            LowRecoveryPotentialRule(),
            UnreasonableDelayRule()
        ]

    def evaluate_decision(
        self,
        features: PaymentFeatureInputs,
        decision: RecoveryDecision
    ) -> GuardrailResult:
        """
        Evaluates a proposed RecoveryDecision against all guardrail safety rules.
        AI HAS ZERO AUTHORITY TO OVERRIDE THIS EVALUATION.
        Returns a deterministic GuardrailResult object.
        """
        rules_evaluated: List[str] = []
        rules_triggered: List[str] = []
        rule_details: List[GuardrailRuleEvaluation] = []
        
        has_block = False
        has_modify = False
        block_reasons = []
        modify_reasons = []

        # 1. Run All Registered Rules Independently
        for rule in self.rules:
            eval_res = rule.evaluate(features=features, decision=decision, config=self.config)
            rules_evaluated.append(rule.rule_id)
            rule_details.append(eval_res)

            if eval_res.status == GuardrailStatus.BLOCK:
                has_block = True
                rules_triggered.append(rule.rule_id)
                block_reasons.append(eval_res.message)
            elif eval_res.status == GuardrailStatus.MODIFY:
                has_modify = True
                rules_triggered.append(rule.rule_id)
                modify_reasons.append(eval_res.message)

        # 2. Determine Aggregate Guardrail Status & Final Action
        original_action = decision.action
        final_action = original_action
        status = GuardrailStatus.ALLOW
        risk_level = "LOW"
        requires_human_review = False

        if has_block:
            status = GuardrailStatus.BLOCK
            risk_level = "HIGH"
            reason = " | ".join(block_reasons)
            # Default final action on BLOCK: STOP (or HUMAN_REVIEW if action was already STOP)
            final_action = RecoveryAction.STOP if original_action != RecoveryAction.STOP else RecoveryAction.STOP
        elif has_modify:
            status = GuardrailStatus.MODIFY
            risk_level = "HIGH" if features.amount >= self.config.HIGH_VALUE_THRESHOLD else "MEDIUM"
            requires_human_review = True
            reason = " | ".join(modify_reasons)
            
            # If high value threshold modified, route to HUMAN_REVIEW
            if "HIGH_VALUE_REVIEW" in rules_triggered:
                final_action = RecoveryAction.HUMAN_REVIEW
            else:
                final_action = RecoveryAction.HUMAN_REVIEW
        else:
            status = GuardrailStatus.ALLOW
            reason = f"Passed: Action '{original_action.value}' satisfied all {len(rules_evaluated)} guardrail rules."
            if original_action == RecoveryAction.HUMAN_REVIEW:
                requires_human_review = True
                risk_level = "MEDIUM"

        return GuardrailResult(
            payment_id=features.payment_id,
            original_action=original_action,
            final_action=final_action,
            status=status,
            rules_evaluated=rules_evaluated,
            rules_triggered=rules_triggered,
            reason=reason,
            risk_level=risk_level,
            requires_human_review=requires_human_review,
            rule_details=rule_details
        )

# Singleton Guardrail Engine Instance
guardrail_engine = GuardrailEngine()
