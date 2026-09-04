"""
RecoverAI - LLM Provider Abstraction Layer
Supports interchangeable LLM backends (Mock Provider for zero-cost offline testing,
and Gemini/OpenAI Providers for live production LLM integration).
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryDecision, RecoveryAction
from ai.scoring import RecoveryScoreResult
from ai.prompts import DECISION_AGENT_SYSTEM_PROMPT_V1

class LLMProvider(ABC):
    """Abstract interface for LLM Decision Providers."""
    
    @abstractmethod
    def generate_decision(self, features: PaymentFeatureInputs, score_result: RecoveryScoreResult) -> RecoveryDecision:
        """Generates a structured RecoveryDecision recommendation."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Deterministic rule-aware Mock LLM Provider for 100% offline, zero-cost,
    reproducible automated testing and evaluations.
    """
    def generate_decision(self, features: PaymentFeatureInputs, score_result: RecoveryScoreResult) -> RecoveryDecision:
        payment_id = features.payment_id
        amount = features.amount
        failure_reason = features.failure_reason.lower()
        payment_method = features.payment_method.lower()
        prev_attempts = features.previous_attempts
        prev_recovery_attempts = features.previous_recovery_attempts
        cust_success_rate = features.customer_success_rate
        ev = score_result.expected_recovery_value
        prob = score_result.recovery_probability
        priority = score_result.priority

        # Action Selection Heuristics
        # 1. PERMANENT BLOCKAGE -> STOP
        if failure_reason == "account_blocked":
            return RecoveryDecision(
                payment_id=payment_id,
                action=RecoveryAction.STOP,
                confidence=0.95,
                rationale=f"Account is blocked; recovery potential is near zero. Ceasing recovery attempts to prevent customer friction.",
                expected_recovery_value=ev,
                priority="LOW",
                recommended_delay_minutes=0,
                risk_level="LOW",
                guardrail_notes="Account blocked failure code; STOP recommended."
            )

        # 2. EXCESSIVE RECOVERY ATTEMPTS -> STOP
        if prev_recovery_attempts >= 3:
            return RecoveryDecision(
                payment_id=payment_id,
                action=RecoveryAction.STOP,
                confidence=0.90,
                rationale=f"Payment has reached the maximum of {prev_recovery_attempts} prior recovery attempts.",
                expected_recovery_value=ev,
                priority="LOW",
                recommended_delay_minutes=0,
                risk_level="LOW",
                guardrail_notes="Maximum attempt threshold reached."
            )

        # 3. AMBIGUOUS / HIGH RISK / LOW SUCCESS RATE -> HUMAN_REVIEW
        if cust_success_rate < 0.20 or prob < 0.20:
            return RecoveryDecision(
                payment_id=payment_id,
                action=RecoveryAction.HUMAN_REVIEW,
                confidence=0.75,
                rationale=f"Customer has a low success rate ({cust_success_rate*100:.0f}%) and low recovery probability ({prob*100:.1f}%); manual merchant review advised.",
                expected_recovery_value=ev,
                priority="LOW",
                recommended_delay_minutes=0,
                risk_level="MEDIUM",
                guardrail_notes="Low customer historical success rate requiring human review."
            )

        # 4. RECENT GATEWAY SPIKE (< 15 MINS) -> WAIT
        if features.time_since_failure_minutes < 15.0 and failure_reason == "network_failure":
            return RecoveryDecision(
                payment_id=payment_id,
                action=RecoveryAction.WAIT,
                confidence=0.82,
                rationale=f"Recent network failure ({features.time_since_failure_minutes:.0f} mins ago); delaying recovery by 30 minutes for gateway stabilization.",
                expected_recovery_value=ev,
                priority=priority,
                recommended_delay_minutes=30,
                risk_level="LOW",
                guardrail_notes="Temporary gateway stabilization delay."
            )

        # 5. HIGH PROBABILITY & TRANSIENT FAILURE & NO PRIOR RECOVERY ATTEMPT -> RETRY
        if failure_reason in ["temporary_bank_error", "network_failure", "3ds_timeout"] and prev_recovery_attempts == 0 and prob >= 0.50:
            return RecoveryDecision(
                payment_id=payment_id,
                action=RecoveryAction.RETRY,
                confidence=0.88,
                rationale=f"Transient failure code '{failure_reason}' via {payment_method.upper()} with no prior recovery attempt; immediate gateway retry recommended.",
                expected_recovery_value=ev,
                priority=priority,
                recommended_delay_minutes=0,
                risk_level="LOW",
                guardrail_notes="Transient error with zero prior recovery attempts."
            )

        # 6. PAYMENT METHOD ISSUE OR PRIOR RETRY FAILED -> PAYMENT_LINK
        if failure_reason in ["insufficient_funds", "customer_abandonment", "payment_method_issue", "authentication_failure"] or prev_recovery_attempts > 0:
            return RecoveryDecision(
                payment_id=payment_id,
                action=RecoveryAction.PAYMENT_LINK,
                confidence=0.85,
                rationale=f"Failure reason '{failure_reason}' suggests an alternate payment path; sending a Payment Link to customer with {cust_success_rate*100:.0f}% payment history.",
                expected_recovery_value=ev,
                priority=priority,
                recommended_delay_minutes=0,
                risk_level="LOW",
                guardrail_notes="Payment Link recommended for alternative payment method."
            )

        # DEFAULT FALLBACK ACTION -> PAYMENT_LINK
        return RecoveryDecision(
            payment_id=payment_id,
            action=RecoveryAction.PAYMENT_LINK,
            confidence=0.80,
            rationale=f"Payment failure '{failure_reason}'; recommending Payment Link intervention.",
            expected_recovery_value=ev,
            priority=priority,
            recommended_delay_minutes=0,
            risk_level="LOW",
            guardrail_notes="Standard Payment Link recommendation."
        )


class RealLLMProvider(LLMProvider):
    """
    Production LLM Provider Integration (Supports Google Gemini & OpenAI API).
    Safe credential validation using environment variables.
    """
    def __init__(self, provider_name: str = "gemini", model_name: Optional[str] = None):
        self.provider_name = provider_name.lower()
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name or os.getenv("LLM_MODEL") or ("gemini-1.5-flash" if self.provider_name == "gemini" else "gpt-4o-mini")

    def validate_configuration(self):
        """Checks whether required credentials and API key environment variables exist."""
        if not self.api_key:
            raise ValueError(
                f"LLM API Key missing! Please set LLM_API_KEY or GEMINI_API_KEY environment variable. "
                "For zero-cost offline testing, use MockLLMProvider."
            )

    def generate_decision(self, features: PaymentFeatureInputs, score_result: RecoveryScoreResult) -> RecoveryDecision:
        self.validate_configuration()

        user_prompt = f"""
Payment Feature Context:
- Payment ID: {features.payment_id}
- Amount: INR {features.amount:.2f}
- Payment Method: {features.payment_method}
- Failure Reason: {features.failure_reason}
- Previous Attempts: {features.previous_attempts}
- Previous Recovery Attempts: {features.previous_recovery_attempts}
- Minutes Since Failure: {features.time_since_failure_minutes:.1f}
- Customer Success Rate: {features.customer_success_rate * 100:.1f}%
- Customer Lifetime Value: INR {features.customer_lifetime_value:.2f}

Scoring Engine Evaluation:
- Recovery Score: {score_result.recovery_score:.1f} / 100
- Calibrated Probability: {score_result.recovery_probability:.4f}
- Expected Recovery Value: INR {score_result.expected_recovery_value:.2f}
- Priority Tier: {score_result.priority}

Recommend the optimal RecoveryDecision JSON.
"""
        # Execute API call depending on SDK installed
        try:
            if self.provider_name == "gemini":
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(
                    DECISION_AGENT_SYSTEM_PROMPT_V1 + "\n\n" + user_prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                raw_text = response.text
            else:
                import openai
                client = openai.OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": DECISION_AGENT_SYSTEM_PROMPT_V1},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_text = response.choices[0].message.content

            data = json.loads(raw_text)
            data["payment_id"] = features.payment_id
            return RecoveryDecision(**data)
        except Exception as err:
            # Safe Fallback to HUMAN_REVIEW on validation/API error
            return RecoveryDecision(
                payment_id=features.payment_id,
                action=RecoveryAction.HUMAN_REVIEW,
                confidence=0.0,
                rationale=f"LLM decision service fallback: {str(err)}",
                expected_recovery_value=score_result.expected_recovery_value,
                priority=score_result.priority,
                recommended_delay_minutes=0,
                risk_level="HIGH",
                guardrail_notes="Validation fallback triggered."
            )


def get_llm_provider(provider_type: Optional[str] = None) -> LLMProvider:
    """
    Factory function returning active LLMProvider instance.
    Defaults to MockLLMProvider unless provider_type='real' or LLM_PROVIDER='real' is set.
    """
    env_provider = os.getenv("LLM_PROVIDER", "mock").lower()
    selected = (provider_type or env_provider).lower()
    
    if selected == "real":
        return RealLLMProvider()
    return MockLLMProvider()
