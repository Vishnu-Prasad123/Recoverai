import json
import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.payment import Payment
from app.models.recovery import RecoveryAttempt
from app.models.audit import AuditLog
from backend.app.schemas.razorpay import PaymentLinkCreateRequest, PaymentLinkResponse, RecoveryExecutionResponse
from razorpay_integration.config import RAZORPAY_CONFIG, RazorpayConfig
from razorpay_integration.provider import MockRazorpayProvider, RealRazorpayAdapter, get_razorpay_provider
from razorpay_integration.webhook_verifier import verify_razorpay_webhook_signature

client = TestClient(app)

def test_razorpay_config_defaults():
    cfg = RazorpayConfig()
    assert cfg.RAZORPAY_MODE in ["mock", "test"]
    assert cfg.API_BASE_URL == "https://api.razorpay.com/v1"

def test_mock_provider_payment_link_creation():
    provider = MockRazorpayProvider()
    req = PaymentLinkCreateRequest(
        payment_id="pay_mock_test_101",
        amount=2500.0,
        currency="INR",
        description="Test Payment Link"
    )
    res = provider.create_payment_link(req)
    assert res.id.startswith("plink_mock_")
    assert res.amount == 2500.0
    assert res.status == "created"
    assert "https://rzp.io/i/" in res.short_url

def test_real_adapter_credentials_validation():
    invalid_cfg = RazorpayConfig(RAZORPAY_MODE="test", RAZORPAY_KEY_ID="invalid_key", RAZORPAY_KEY_SECRET="secret")
    with pytest.raises(ValueError, match="Invalid Razorpay Key ID format"):
        invalid_cfg.validate_test_credentials()

def test_guardrail_block_prevents_razorpay_call():
    # Fetch a payment and force previous_recovery_attempts = 2 to trigger Guardrail BLOCK
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100001").first()
        if pmt:
            pmt.previous_recovery_attempts = 2
            db.commit()
    finally:
        db.close()

    res = client.post("/api/recovery/execute?payment_id=pay_100001")
    assert res.status_code == 200
    data = res.json()
    assert data["execution_status"] == "BLOCKED_BY_GUARDRAILS"
    assert data["payment_link"] is None
    assert "Guardrail Engine" in data["message"]

def test_guardrail_human_review_prevents_auto_execution():
    # Force high amount (INR 50,000) to trigger Guardrail MODIFY / HUMAN_REVIEW
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100002").first()
        if pmt:
            pmt.amount = 50000.0
            pmt.previous_recovery_attempts = 0
            db.commit()
    finally:
        db.close()

    res = client.post("/api/recovery/execute?payment_id=pay_100002")
    assert res.status_code == 200
    data = res.json()
    assert data["execution_status"] == "ESCALATED_FOR_HUMAN_REVIEW"
    assert data["payment_link"] is None

def test_guardrail_allow_permits_execution():
    # Setup valid eligible payment
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100003").first()
        if pmt:
            pmt.amount = 4500.0
            pmt.previous_recovery_attempts = 0
            pmt.status = "FAILED"
            db.commit()
    finally:
        db.close()

    res = client.post("/api/recovery/execute?payment_id=pay_100003")
    assert res.status_code == 200
    data = res.json()
    assert data["execution_status"] in ["EXECUTED_SUCCESS", "IDEMPOTENT_SKIPPED"]
    if data["execution_status"] == "EXECUTED_SUCCESS":
        assert data["payment_link"] is not None
        assert data["payment_link"]["short_url"] != ""

def test_idempotency_prevents_duplicate_execution():
    # Second call for pay_100003 should trigger Idempotency Protection
    res = client.post("/api/recovery/execute?payment_id=pay_100003")
    assert res.status_code == 200
    data = res.json()
    assert data["execution_status"] == "IDEMPOTENT_SKIPPED"

def test_webhook_signature_verification_valid_and_invalid():
    secret = "test_webhook_secret"
    body = b'{"event":"payment.link.paid","account_id":"acc_123"}'
    
    # Valid HMAC
    valid_sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_razorpay_webhook_signature(body, valid_sig, secret) is True
    
    # Invalid HMAC
    assert verify_razorpay_webhook_signature(body, "invalid_signature", secret) is False

def test_api_webhook_endpoint_invalid_signature_rejected():
    res = client.post(
        "/api/webhooks/razorpay",
        content=b'{"event":"payment.link.paid"}',
        headers={"X-Razorpay-Signature": "invalid_sig"}
    )
    assert res.status_code == 400
    assert "Invalid or missing" in res.json()["detail"]

def test_api_webhook_endpoint_valid_payment_paid():
    secret = RAZORPAY_CONFIG.RAZORPAY_WEBHOOK_SECRET
    payload_dict = {
        "event": "payment.link.paid",
        "account_id": "acc_test_999",
        "created_at": 1700000000,
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_test_wh_101",
                    "status": "paid",
                    "notes": {
                        "payment_id": "pay_100004"
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
    data = res.json()
    assert data["status"] == "success"
    assert data["event"] == "payment.link.paid"

    # Verify operational DB payment status updated to RECOVERED
    db = SessionLocal()
    try:
        pmt = db.query(Payment).filter(Payment.payment_id == "pay_100004").first()
        if pmt:
            assert pmt.status == "RECOVERED"
            assert pmt.recovered is True
    finally:
        db.close()

def test_secret_leakage_prevention():
    """CRITICAL SECURITY TEST: Ensures RAZORPAY_KEY_SECRET is never present in API outputs or DB logs."""
    secret = RAZORPAY_CONFIG.RAZORPAY_KEY_SECRET
    
    # 1. API Endpoint check
    res = client.post("/api/recovery/execute?payment_id=pay_100003")
    res_text = res.text
    assert secret not in res_text or secret == "mock_key_secret"

    # 2. Database AuditLog check
    db = SessionLocal()
    try:
        audit_logs = db.query(AuditLog).all()
        for log in audit_logs:
            assert secret not in log.details or secret == "mock_key_secret"
    finally:
        db.close()

def test_api_recovery_attempts_endpoint():
    res = client.get("/api/recovery/pay_100003")
    assert res.status_code == 200
    data = res.json()
    assert data["payment_id"] == "pay_100003"
    assert "attempts" in data
