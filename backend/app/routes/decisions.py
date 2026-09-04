from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.decision import RecoveryDecision, DecisionPreviewRequest, BatchDecisionPreviewRequest
from app.services.decision_service import DecisionService
from app.services.payment_service import PaymentService
from ai.agent import ai_decision_agent
from ai.scoring import scoring_engine

router = APIRouter(prefix="/api/decisions", tags=["AI Decisions"])

@router.post("/preview", response_model=RecoveryDecision)
def preview_decision(
    req: DecisionPreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates AI Recovery Decision preview for a payment record.
    CRITICAL: Does NOT execute any real recovery intervention.
    """
    if req.payment_id:
        decision = DecisionService.preview_decision_by_id(db, payment_id=req.payment_id)
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment ID '{req.payment_id}' not found."
            )
        return decision

    # If raw features provided in body
    if req.amount and req.payment_method and req.failure_reason:
        from datetime import datetime, timezone
        from app.schemas.payment import PaymentFeatureInputs
        feat = PaymentFeatureInputs(
            payment_id="pay_preview_adhoc",
            customer_id="cust_preview",
            amount=req.amount,
            currency="INR",
            payment_method=req.payment_method,
            failure_reason=req.failure_reason,
            timestamp=datetime.now(timezone.utc),
            previous_attempts=1,
            previous_recovery_attempts=0,
            time_since_failure_minutes=15.0,
            customer_success_rate=0.75,
            customer_lifetime_value=15000.0,
            customer_previous_payments=5,
        )
        return ai_decision_agent.recommend_action(features=feat)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Must provide either 'payment_id' or transaction feature parameters ('amount', 'payment_method', 'failure_reason')."
    )

@router.post("/batch-preview", response_model=List[RecoveryDecision])
def preview_batch_decisions(
    req: BatchDecisionPreviewRequest,
    db: Session = Depends(get_db)
):
    """Batch decision preview for multiple payment IDs."""
    if not req.payment_ids:
        return []
    return DecisionService.preview_decisions_batch(db, payment_ids=req.payment_ids)
