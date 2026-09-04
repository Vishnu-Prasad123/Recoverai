import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.recovery import RecoveryAttempt
from app.models.audit import AuditLog
from app.services.payment_service import PaymentService
from app.services.decision_service import DecisionService
from app.services.guardrail_service import GuardrailService
from ai.scoring import scoring_engine
from ai.agent import ai_decision_agent
from guardrails.engine import guardrail_engine
from app.schemas.decision import RecoveryAction, RecoveryDecision
from app.schemas.guardrail import GuardrailStatus, GuardrailResult
from app.schemas.razorpay import (
    PaymentLinkCreateRequest,
    PaymentLinkResponse,
    RecoveryExecutionResponse
)
from razorpay_integration.provider import get_razorpay_provider, RazorpayProvider

class RecoveryExecutionService:
    @staticmethod
    def execute_full_recovery_pipeline(
        db: Session,
        payment_id: str,
        provider: Optional[RazorpayProvider] = None
    ) -> Optional[RecoveryExecutionResponse]:
        """
        Unified 5-Step End-to-End Recovery Execution Pipeline.
        
        PIPELINE FLOW:
        1. Feature Extraction & Scoring Engine -> Recovery Score, P, EV
        2. AI Decision Agent -> Proposed Action & Rationale
        3. Independent Guardrail Engine -> Deterministic Rule Evaluation (ALLOW / MODIFY / BLOCK)
        4. Safety Gate Check -> If BLOCK or HUMAN_REVIEW, STOP & DO NOT call Razorpay API.
           If ALLOW -> Check Idempotency & Execute via Razorpay Provider.
        5. Database Persistence & Audit Trail -> Record RecoveryAttempt & AuditLog.
        """
        # 1. Feature Extraction & Scoring Engine
        feat = PaymentService.get_payment_feature_inputs(db, payment_id=payment_id)
        if not feat:
            return None

        pmt_orm = PaymentService.get_payment_by_id(db, payment_id=payment_id)
        if pmt_orm:
            feat.status = pmt_orm.status

        scoring_res = scoring_engine.score_payment(feat)
        now_str = datetime.now(timezone.utc).isoformat()

        # 2. AI Decision Agent Recommendation
        ai_decision: RecoveryDecision = ai_decision_agent.recommend_action(feat)

        # 3. Independent Guardrail Engine Evaluation
        g_result: GuardrailResult = guardrail_engine.evaluate_decision(features=feat, decision=ai_decision)

        # 4. Safety Gate Check: Guardrail BLOCK or HUMAN_REVIEW
        if g_result.status == GuardrailStatus.BLOCK:
            audit_id = RecoveryExecutionService._record_execution_audit(
                db, payment_id, g_result, "BLOCKED_BY_GUARDRAILS", "External API call prevented by Guardrail BLOCK."
            )
            return RecoveryExecutionResponse(
                payment_id=payment_id,
                guardrail_status=g_result.status,
                original_action=g_result.original_action,
                final_action=g_result.final_action,
                execution_status="BLOCKED_BY_GUARDRAILS",
                payment_link=None,
                audit_id=audit_id,
                executed_at=now_str,
                message=f"Execution prevented by Guardrail Engine: {g_result.reason}"
            )

        if g_result.status == GuardrailStatus.MODIFY or g_result.requires_human_review:
            audit_id = RecoveryExecutionService._record_execution_audit(
                db, payment_id, g_result, "ESCALATED_FOR_HUMAN_REVIEW", "Automatic execution paused for merchant review."
            )
            return RecoveryExecutionResponse(
                payment_id=payment_id,
                guardrail_status=g_result.status,
                original_action=g_result.original_action,
                final_action=g_result.final_action,
                execution_status="ESCALATED_FOR_HUMAN_REVIEW",
                payment_link=None,
                audit_id=audit_id,
                executed_at=now_str,
                message=f"Automatic execution paused for merchant review: {g_result.reason}"
            )

        # 5. Idempotency Check (Prevent duplicate links for same recovery attempt)
        existing_attempt = db.query(RecoveryAttempt).filter(
            RecoveryAttempt.payment_id == payment_id,
            RecoveryAttempt.action_type == g_result.final_action.value
        ).order_by(RecoveryAttempt.created_at.desc()).first()

        if existing_attempt and existing_attempt.status in ["SUCCESS", "PENDING"]:
            link_data = None
            if existing_attempt.response_payload:
                try:
                    det = json.loads(existing_attempt.response_payload)
                    link_data = PaymentLinkResponse(
                        id=det.get("id", "plink_existing"),
                        amount=float(det.get("amount", pmt_orm.amount if pmt_orm else 0.0)),
                        currency="INR",
                        status=existing_attempt.status.lower(),
                        short_url=det.get("short_url", ""),
                        created_at=int(datetime.now().timestamp())
                    )
                except Exception:
                    pass
            audit_id = RecoveryExecutionService._record_execution_audit(
                db, payment_id, g_result, "IDEMPOTENT_SKIPPED", "Duplicate execution request skipped."
            )
            return RecoveryExecutionResponse(
                payment_id=payment_id,
                guardrail_status=g_result.status,
                original_action=g_result.original_action,
                final_action=g_result.final_action,
                execution_status="IDEMPOTENT_SKIPPED",
                payment_link=link_data,
                audit_id=audit_id,
                executed_at=now_str,
                message="Idempotency protection: Duplicate recovery execution skipped. Existing active attempt returned."
            )

        # 6. Execute Allowed Action via Razorpay Provider
        pz_provider = provider or get_razorpay_provider()
        plink_resp: Optional[PaymentLinkResponse] = None

        if g_result.final_action == RecoveryAction.PAYMENT_LINK:
            req = PaymentLinkCreateRequest(
                payment_id=payment_id,
                amount=pmt_orm.amount if pmt_orm else 0.0,
                currency=pmt_orm.currency if pmt_orm else "INR",
                description=f"RecoverAI Payment Link for Payment {payment_id}",
                customer_name=f"Customer {pmt_orm.customer_id}" if pmt_orm else "Valued Customer",
                customer_email="customer@example.com"
            )
            plink_resp = pz_provider.create_payment_link(req)

        elif g_result.final_action == RecoveryAction.RETRY:
            plink_resp = PaymentLinkResponse(
                id=f"retry_{uuid.uuid4().hex[:8]}",
                amount=pmt_orm.amount if pmt_orm else 0.0,
                currency=pmt_orm.currency if pmt_orm else "INR",
                status="created",
                short_url=f"https://api.razorpay.com/v1/payments/{payment_id}/retry",
                created_at=int(datetime.now().timestamp())
            )

        # 7. Record RecoveryAttempt Entity & Update Operational Status
        attempt_id = f"att_{uuid.uuid4().hex[:12]}"
        new_attempt = RecoveryAttempt(
            attempt_id=attempt_id,
            payment_id=payment_id,
            attempt_number=(pmt_orm.previous_recovery_attempts + 1) if pmt_orm else 1,
            action_type=g_result.final_action.value,
            status="PENDING" if g_result.final_action == RecoveryAction.PAYMENT_LINK else "SUCCESS",
            response_payload=json.dumps(plink_resp.model_dump()) if plink_resp else None
        )
        db.add(new_attempt)

        if pmt_orm:
            pmt_orm.previous_recovery_attempts += 1
            if pmt_orm.status == "FAILED":
                pmt_orm.status = "RECOVERY_INITIATED"
        db.commit()

        audit_id = RecoveryExecutionService._record_execution_audit(
            db, payment_id, g_result, "EXECUTED_SUCCESS", f"Action {g_result.final_action.value} executed successfully."
        )

        return RecoveryExecutionResponse(
            payment_id=payment_id,
            guardrail_status=g_result.status,
            original_action=g_result.original_action,
            final_action=g_result.final_action,
            execution_status="EXECUTED_SUCCESS",
            payment_link=plink_resp,
            audit_id=audit_id,
            executed_at=now_str,
            message=f"Action '{g_result.final_action.value}' executed successfully via {pz_provider.__class__.__name__}."
        )

    @staticmethod
    def execute_payment_recovery(
        db: Session,
        payment_id: str,
        provider: Optional[RazorpayProvider] = None
    ) -> Optional[RecoveryExecutionResponse]:
        """Backward-compatible alias invoking full recovery pipeline."""
        return RecoveryExecutionService.execute_full_recovery_pipeline(db, payment_id, provider)

    @staticmethod
    def _record_execution_audit(
        db: Session,
        payment_id: str,
        g_result: GuardrailResult,
        exec_status: str,
        message: str
    ) -> str:
        pmt = PaymentService.get_payment_by_id(db, payment_id=payment_id)
        cust_id = pmt.customer_id if pmt else "cust_unknown"
        audit_entry = AuditLog(
            log_id=f"audit_exec_{uuid.uuid4().hex[:10]}",
            payment_id=payment_id,
            customer_id=cust_id,
            event_type=f"RECOVERY_EXECUTION_{exec_status}",
            actor="RECOVERY_EXECUTION_SERVICE",
            details=json.dumps({
                "guardrail_status": g_result.status.value,
                "original_action": g_result.original_action.value,
                "final_action": g_result.final_action.value,
                "execution_status": exec_status,
                "message": message
            })
        )
        db.add(audit_entry)
        db.commit()
        return audit_entry.log_id
