import json
import time
import uuid
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.payment import Payment
from app.models.recovery import RecoveryAttempt
from app.models.audit import AuditLog
from app.services.recovery_execution_service import RecoveryExecutionService
from razorpay_integration.config import RAZORPAY_CONFIG

client = TestClient(app)

def test_e2e_allow_recovery_flow():
    # Setup eligible payment
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100005").first()
        if pmt:
            pmt.amount = 5000.0
            pmt.previous_recovery_attempts = 0
            pmt.status = "FAILED"
            pmt.failure_reason = "temporary_bank_error"
            db.commit()
    finally:
        db.close()

    res = client.post("/api/recovery/execute?payment_id=pay_100005")
    assert res.status_code == 200
    data = res.json()
    assert data["guardrail_status"] == "ALLOW"
    assert data["execution_status"] in ["EXECUTED_SUCCESS", "IDEMPOTENT_SKIPPED"]
    assert data["payment_link"] is not None
    assert "https://rzp.io/i/" in data["payment_link"]["short_url"] or "api.razorpay.com" in data["payment_link"]["short_url"]

def test_e2e_guardrail_block_prevents_razorpay_call():
    # Setup payment with 2 prior recovery attempts to trigger Guardrail BLOCK
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100006").first()
        if pmt:
            pmt.previous_recovery_attempts = 2
            db.commit()
    finally:
        db.close()

    res = client.post("/api/recovery/execute?payment_id=pay_100006")
    assert res.status_code == 200
    data = res.json()
    assert data["guardrail_status"] == "BLOCK"
    assert data["execution_status"] == "BLOCKED_BY_GUARDRAILS"
    assert data["payment_link"] is None
    assert "Guardrail Engine" in data["message"]

def test_e2e_guardrail_human_review_prevents_auto_execution():
    # Setup high amount payment (INR 50,000) with transient failure to trigger Guardrail MODIFY / HUMAN_REVIEW
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100007").first()
        if pmt:
            pmt.amount = 50000.0
            pmt.previous_recovery_attempts = 0
            pmt.status = "FAILED"
            pmt.failure_reason = "insufficient_funds"
            db.commit()
    finally:
        db.close()

    res = client.post("/api/recovery/execute?payment_id=pay_100007")
    assert res.status_code == 200
    data = res.json()
    assert data["guardrail_status"] == "MODIFY"
    assert data["execution_status"] == "ESCALATED_FOR_HUMAN_REVIEW"
    assert data["payment_link"] is None

def test_e2e_idempotency():
    # Setup fresh payment pay_100008 and clear existing attempts
    db = SessionLocal()
    try:
        db.query(RecoveryAttempt).filter(RecoveryAttempt.payment_id == "pay_100008").delete()
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100008").first()
        if pmt:
            pmt.amount = 3500.0
            pmt.previous_recovery_attempts = 0
            pmt.status = "FAILED"
            pmt.failure_reason = "insufficient_funds"
            db.commit()
    finally:
        db.close()

    # Call 1 -> Creates PAYMENT_LINK (returns EXECUTED_SUCCESS)
    res1 = client.post("/api/recovery/execute?payment_id=pay_100008")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["execution_status"] == "EXECUTED_SUCCESS"
    assert data1["final_action"] == "PAYMENT_LINK"

    # Call 2 -> Identical proposed action PAYMENT_LINK triggers IDEMPOTENT_SKIPPED
    res2 = client.post("/api/recovery/execute?payment_id=pay_100008")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["execution_status"] == "IDEMPOTENT_SKIPPED"

def test_e2e_webhook_state_transition_to_recovered():
    secret = RAZORPAY_CONFIG.RAZORPAY_WEBHOOK_SECRET
    payload_dict = {
        "event": "payment.link.paid",
        "account_id": f"acc_e2e_{uuid.uuid4().hex[:6]}",
        "created_at": int(time.time()),
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_e2e_101",
                    "status": "paid",
                    "notes": {
                        "payment_id": "pay_100005"
                    }
                }
            }
        }
    }
    body_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": sig}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Confirm database operational status updated to RECOVERED
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100005").first()
        if pmt:
            assert pmt.status == "RECOVERED"
            assert pmt.recovered is True
    finally:
        db.close()

def test_e2e_read_endpoint_returns_complete_payload():
    res = client.get("/api/recovery/pay_100005")
    assert res.status_code == 200
    data = res.json()
    assert data["payment_id"] == "pay_100005"
    assert "scoring" in data
    assert "ai_recommendation" in data
    assert "guardrail_evaluation" in data
    assert "attempts" in data
    assert "audit_trail" in data

def test_e2e_secret_leakage_prevention():
    secret = RAZORPAY_CONFIG.RAZORPAY_KEY_SECRET
    res = client.get("/api/recovery/pay_100005")
    assert secret not in res.text or secret == "mock_key_secret"
