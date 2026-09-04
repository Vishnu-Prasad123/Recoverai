from typing import Optional, List
from sqlalchemy.orm import Session
from app.services.payment_service import PaymentService
from app.services.scoring_service import ScoringService
from app.schemas.decision import RecoveryDecision
from ai.agent import ai_decision_agent
from ai.scoring import scoring_engine

class DecisionService:
    @staticmethod
    def preview_decision_by_id(db: Session, payment_id: str) -> Optional[RecoveryDecision]:
        """
        Extracts features for a database payment and previews the AI Agent decision.
        Does NOT execute any real recovery intervention.
        """
        feat = PaymentService.get_payment_feature_inputs(db, payment_id=payment_id)
        if not feat:
            return None
        score_res = scoring_engine.score_payment(feat)
        return ai_decision_agent.recommend_action(features=feat, score_result=score_res)

    @staticmethod
    def preview_decisions_batch(db: Session, payment_ids: List[str]) -> List[RecoveryDecision]:
        """Batch decision preview for multiple payment IDs."""
        decisions = []
        for p_id in payment_ids:
            dec = DecisionService.preview_decision_by_id(db, payment_id=p_id)
            if dec:
                decisions.append(dec)
        return decisions
