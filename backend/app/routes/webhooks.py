import json
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Request, Header, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.payment import Payment
from app.models.recovery import RecoveryAttempt
from app.models.audit import AuditLog
from razorpay_integration.config import RAZORPAY_CONFIG
from razorpay_integration.webhook_verifier import verify_razorpay_webhook_signature

router = APIRouter(prefix="/api/webhooks", tags=["Razorpay Webhooks"])

@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db)
):
    """
    Razorpay Webhook Handler with HMAC-SHA256 Signature Verification.
    Synchronizes operational payment status (e.g. payment.link.paid -> RECOVERED).
    """
    body_bytes = await request.body()
    
    # 1. Signature Verification
    webhook_secret = RAZORPAY_CONFIG.RAZORPAY_WEBHOOK_SECRET
    if not x_razorpay_signature or not verify_razorpay_webhook_signature(body_bytes, x_razorpay_signature, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing Razorpay Webhook HMAC signature."
        )

    # 2. Parse Event Payload
    try:
        payload_data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON webhook payload."
        )

    event_type = payload_data.get("event", "unknown")
    event_id = payload_data.get("account_id", "") + "_" + str(payload_data.get("created_at", ""))

    # 3. Idempotency Protection: Check if webhook event already processed
    existing_audit = db.query(AuditLog).filter(
        AuditLog.event_type == f"WEBHOOK_{event_type}",
        AuditLog.details.like(f"%{event_id}%")
    ).first()
    if existing_audit:
        return {"status": "success", "event": event_type, "message": "Event already processed (Idempotent)."}

    # 4. Extract Entity Details & Synchronize Operational State
    payload_entity = payload_data.get("payload", {}).get("payment_link", {}).get("entity", {})
    notes = payload_entity.get("notes", {})
    payment_id = notes.get("payment_id") or payload_entity.get("reference_id")

    updated = False
    if payment_id:
        pmt = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if pmt:
            if event_type == "payment.link.paid":
                pmt.status = "RECOVERED"
                pmt.recovered = True
                pmt.amount_recovered = pmt.amount
                updated = True
                
                # Update latest active RecoveryAttempt
                attempt = db.query(RecoveryAttempt).filter(
                    RecoveryAttempt.payment_id == payment_id
                ).order_by(RecoveryAttempt.created_at.desc()).first()
                if attempt:
                    attempt.status = "SUCCESS"

            elif event_type in ["payment.link.expired", "payment.link.cancelled"]:
                pmt.status = "EXPIRED"
                updated = True
                attempt = db.query(RecoveryAttempt).filter(
                    RecoveryAttempt.payment_id == payment_id
                ).order_by(RecoveryAttempt.created_at.desc()).first()
                if attempt:
                    attempt.status = "EXPIRED"

            db.commit()

    # 5. Audit Logging
    audit_entry = AuditLog(
        log_id=f"audit_wh_{uuid.uuid4().hex[:10]}",
        payment_id=payment_id or "pay_unknown",
        customer_id=pmt.customer_id if payment_id and pmt else "cust_unknown",
        event_type=f"WEBHOOK_{event_type}",
        actor="RAZORPAY_WEBHOOK",
        details=json.dumps({
            "event_id": event_id,
            "event_type": event_type,
            "payment_id": payment_id,
            "state_updated": updated
        })
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "success",
        "event": event_type,
        "payment_id": payment_id,
        "state_updated": updated
    }
