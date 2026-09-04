import json
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.services.payment_service import PaymentService
from app.services.decision_service import DecisionService
from app.schemas.decision import RecoveryDecision, RecoveryAction
from app.schemas.guardrail import GuardrailResult, GuardrailStatus
from guardrails.engine import guardrail_engine

class GuardrailService:
    @staticmethod
    def evaluate_payment_guardrails(
        db: Session,
        payment_id: str,
        proposed_action: Optional[RecoveryAction] = None
    ) -> Optional[GuardrailResult]:
        """
        Evaluates Guardrail Engine rules for a payment and logs audit trail.
        Does NOT execute any real recovery intervention.
        """
        feat = PaymentService.get_payment_feature_inputs(db, payment_id=payment_id)
        if not feat:
            return None

        # Fetch payment ORM record to attach operational status
        pmt_orm = PaymentService.get_payment_by_id(db, payment_id=payment_id)
        if pmt_orm:
            feat.status = pmt_orm.status

        # Obtain proposed decision from AI Decision Agent if proposed_action not explicitly supplied
        decision = DecisionService.preview_decision_by_id(db, payment_id=payment_id)
        if proposed_action and decision:
            decision.action = proposed_action

        if not decision:
            return None

        # Run Independent Guardrail Engine
        result = guardrail_engine.evaluate_decision(features=feat, decision=decision)

        # Audit Logging: Record immutable entry in AuditLog entity
        cust_id = pmt_orm.customer_id if pmt_orm else "cust_unknown"
        audit_entry = AuditLog(
            log_id=f"audit_{uuid.uuid4().hex[:12]}",
            payment_id=payment_id,
            customer_id=cust_id,
            event_type=f"GUARDRAIL_{result.status.value}",
            actor="GUARDRAIL_ENGINE",
            details=json.dumps({
                "original_action": result.original_action.value,
                "final_action": result.final_action.value,
                "status": result.status.value,
                "rules_evaluated": result.rules_evaluated,
                "rules_triggered": result.rules_triggered,
                "reason": result.reason,
                "risk_level": result.risk_level,
                "requires_human_review": result.requires_human_review
            })
        )
        db.add(audit_entry)
        db.commit()

        return result
