import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.razorpay import RecoveryExecutionResponse, PaymentLinkResponse, PaymentLinkCreateRequest
from app.services.recovery_execution_service import RecoveryExecutionService
from app.services.payment_service import PaymentService
from app.services.decision_service import DecisionService
from app.models.recovery import RecoveryAttempt
from app.models.audit import AuditLog
from ai.scoring import scoring_engine
from guardrails.engine import guardrail_engine

router = APIRouter(prefix="/api/recovery", tags=["Recovery Execution"])

@router.post("/execute", response_model=RecoveryExecutionResponse)
def execute_recovery(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """
    Executes Unified 5-Step End-to-End Recovery Pipeline for a failed payment.
    PIPELINE: Scoring -> AI Decision -> Guardrail Engine -> Safety Gate -> Razorpay Provider -> Persistence.
    CRITICAL: Automatic execution is STRICTLY PREVENTED if Guardrail status is BLOCK or HUMAN_REVIEW.
    """
    res = RecoveryExecutionService.execute_full_recovery_pipeline(db, payment_id=payment_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment ID '{payment_id}' not found."
        )
    return res


@router.post("/payment-link", response_model=RecoveryExecutionResponse)
def create_payment_link_endpoint(
    req: PaymentLinkCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Creates a Razorpay Payment Link for an eligible payment.
    Enforces Guardrail Engine ALLOW check before issuing Payment Link API call.
    """
    res = RecoveryExecutionService.execute_full_recovery_pipeline(db, payment_id=req.payment_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment ID '{req.payment_id}' not found."
        )
    return res


@router.get("/{payment_id}")
def get_recovery_status(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves comprehensive recovery status, scoring metrics, AI decision, guardrail evaluation,
    and attempt history for a payment.
    """
    feat = PaymentService.get_payment_feature_inputs(db, payment_id=payment_id)
    pmt_orm = PaymentService.get_payment_by_id(db, payment_id=payment_id)
    if not pmt_orm or not feat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment ID '{payment_id}' not found."
        )

    # 1. Scoring Metrics
    feat.status = pmt_orm.status
    scoring_res = scoring_engine.score_payment(feat)

    # 2. AI Decision Preview
    ai_dec = DecisionService.preview_decision_by_id(db, payment_id=payment_id)

    # 3. Guardrail Evaluation Preview
    g_res = guardrail_engine.evaluate_decision(feat, ai_dec) if ai_dec else None

    # 4. Attempt History & Audit Logs
    attempts = db.query(RecoveryAttempt).filter(
        RecoveryAttempt.payment_id == payment_id
    ).order_by(RecoveryAttempt.created_at.desc()).all()

    audit_logs = db.query(AuditLog).filter(
        AuditLog.payment_id == payment_id
    ).order_by(AuditLog.created_at.desc()).all()

    return {
        "payment_id": payment_id,
        "customer_id": pmt_orm.customer_id,
        "amount": pmt_orm.amount,
        "currency": pmt_orm.currency,
        "payment_method": pmt_orm.payment_method,
        "failure_reason": pmt_orm.failure_reason,
        "operational_status": pmt_orm.status,
        "previous_recovery_attempts": pmt_orm.previous_recovery_attempts,
        "scoring": {
            "recovery_score": scoring_res.recovery_score,
            "recovery_probability": scoring_res.recovery_probability,
            "expected_recovery_value": scoring_res.expected_recovery_value,
            "priority": scoring_res.priority
        },
        "ai_recommendation": ai_dec.model_dump() if ai_dec else None,
        "guardrail_evaluation": g_res.model_dump() if g_res else None,
        "attempts": [
            {
                "attempt_id": att.attempt_id,
                "attempt_number": att.attempt_number,
                "action": att.action_type,
                "status": att.status,
                "response_payload": json.loads(att.response_payload) if att.response_payload else None,
                "created_at": str(att.created_at)
            }
            for att in attempts
        ],
        "audit_trail": [
            {
                "log_id": log.log_id,
                "event_type": log.event_type,
                "actor": log.actor,
                "details": json.loads(log.details) if log.details else None,
                "created_at": str(log.created_at)
            }
            for log in audit_logs
        ]
    }
