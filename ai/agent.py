"""
RecoverAI - Core AI Decision Agent Engine
Orchestrates pre-decision feature extraction, Phase 4 Scoring Engine evaluation,
and LLM Provider action recommendation with Pydantic validation & safe fallback handling.
"""

from typing import Dict, List, Any, Union, Optional
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryDecision, RecoveryAction
from ai.scoring import scoring_engine, RecoveryScoreResult
from ai.llm_provider import get_llm_provider, LLMProvider

class AIDecisionAgent:
    """
    AI Decision Agent for merchant revenue recovery.
    Answers: "What action should we recommend for this failed payment?"
    """
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()

    def _check_data_leakage(self, features_dict: Dict[str, Any]):
        """CRITICAL: Rejects input objects containing ground-truth evaluation labels."""
        forbidden_fields = {"recovered", "amount_recovered", "true_recovery_probability"}
        leaked = set(features_dict.keys()).intersection(forbidden_fields)
        if leaked:
            raise ValueError(
                f"DATA LEAKAGE DETECTED! Feature set contains ground-truth evaluation labels: {leaked}. "
                "The AI Decision Agent must ONLY evaluate pre-decision feature inputs."
            )

    def recommend_action(
        self,
        features: Union[PaymentFeatureInputs, Dict[str, Any]],
        score_result: Optional[RecoveryScoreResult] = None
    ) -> RecoveryDecision:
        """
        Recommends a validated RecoveryDecision for a single payment.
        Input MUST contain pre-decision features ONLY.
        """
        if isinstance(features, PaymentFeatureInputs):
            feat_dict = features.model_dump()
            feat_obj = features
        elif isinstance(features, dict):
            feat_dict = features
            self._check_data_leakage(feat_dict)
            feat_obj = PaymentFeatureInputs(**feat_dict)
        else:
            raise TypeError("features must be an instance of PaymentFeatureInputs or dict")

        # 1. Enforce Data Leakage Protection
        self._check_data_leakage(feat_dict)

        # 2. Get Scoring Engine Evaluation if not provided
        if score_result is None:
            score_result = scoring_engine.score_payment(feat_obj)

        # 3. Call Provider to Generate Structured Decision Recommendation
        try:
            decision = self.provider.generate_decision(features=feat_obj, score_result=score_result)
            
            # Ensure return object is valid RecoveryDecision
            if not isinstance(decision, RecoveryDecision):
                decision = RecoveryDecision(**decision)
                
            return decision

        except Exception as err:
            # 4. SAFE FALLBACK HANDLER
            # If LLM output fails schema validation or API errors out, route to HUMAN_REVIEW safely
            return RecoveryDecision(
                payment_id=feat_obj.payment_id,
                action=RecoveryAction.HUMAN_REVIEW,
                confidence=0.0,
                rationale=f"Decision Engine Fallback: Schema validation failed ({str(err)}). Routed for merchant human review.",
                expected_recovery_value=score_result.expected_recovery_value,
                priority=score_result.priority,
                recommended_delay_minutes=0,
                risk_level="HIGH",
                guardrail_notes="Safe fallback triggered by AI agent parser exception."
            )

    def recommend_action_batch(
        self,
        items: List[Union[PaymentFeatureInputs, Dict[str, Any]]]
    ) -> List[RecoveryDecision]:
        """Recommends recovery decisions for a batch of payments."""
        return [self.recommend_action(item) for item in items]

# Default Agent Instance (uses Mock Provider for zero-cost offline testing)
ai_decision_agent = AIDecisionAgent()
