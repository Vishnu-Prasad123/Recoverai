from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.guardrail import GuardrailResult, GuardrailEvaluationRequest
from app.schemas.decision import RecoveryDecision, RecoveryAction
from app.services.guardrail_service import GuardrailService
from app.services.payment_service import PaymentService
from ai.agent import ai_decision_agent
from guardrails.engine import guardrail_engine

router = APIRouter(prefix="/api/guardrails", tags=["Guardrails"])

@router.post("/evaluate", response_model=GuardrailResult)
def evaluate_guardrails(
    req: GuardrailEvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates Independent Guardrail Engine safety rules for a proposed payment action.
    CRITICAL: Does NOT execute any real recovery intervention.
    """
    if req.payment_id:
        result = GuardrailService.evaluate_payment_guardrails(
            db,
            payment_id=req.payment_id,
            proposed_action=req.proposed_action
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment ID '{req.payment_id}' not found."
            )
        return result

    # Ad-hoc evaluation for uncommitted payload
    if req.amount and req.payment_method and req.failure_reason:
        from datetime import datetime, timezone
        from app.schemas.payment import PaymentFeatureInputs
        feat = PaymentFeatureInputs(
            payment_id="pay_guard_preview",
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
        proposed_decision = ai_decision_agent.recommend_action(features=feat)
        if req.proposed_action:
            proposed_decision.action = req.proposed_action

        return guardrail_engine.evaluate_decision(features=feat, decision=proposed_decision)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Must provide either 'payment_id' or transaction feature parameters ('amount', 'payment_method', 'failure_reason')."
    )
