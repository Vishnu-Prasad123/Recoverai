from typing import Optional, List
from sqlalchemy.orm import Session
from app.services.payment_service import PaymentService
from ai.scoring import scoring_engine, RecoveryScoreResult

class ScoringService:
    @staticmethod
    def score_payment_by_id(db: Session, payment_id: str) -> Optional[RecoveryScoreResult]:
        """
        Extracts pre-decision features for a database payment and evaluates its Recovery Score.
        Returns None if payment is not found.
        """
        features = PaymentService.get_payment_feature_inputs(db, payment_id=payment_id)
        if not features:
            return None
        return scoring_engine.score_payment(features)

    @staticmethod
    def score_all_payments(db: Session) -> List[RecoveryScoreResult]:
        """Scores all payment records currently stored in the database."""
        payments, total, _ = PaymentService.get_payments(db=db, page=1, page_size=10000)
        feature_inputs = []
        for p in payments:
            feat = PaymentService.get_payment_feature_inputs(db, payment_id=p.payment_id)
            if feat:
                feature_inputs.append(feat)
        return scoring_engine.score_batch(feature_inputs)
