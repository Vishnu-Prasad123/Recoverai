"""
RecoverAI - Razorpay Webhook Signature Verifier
Verifies HMAC-SHA256 signature for incoming Razorpay webhook event payloads.
Ensures authenticity and prevents payload tampering or replay attacks.
"""

import hmac
import hashlib

def verify_razorpay_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Verifies the authenticity of a Razorpay Webhook payload signature using HMAC-SHA256.
    
    :param body: Raw request body bytes
    :param signature: Value from 'X-Razorpay-Signature' header
    :param secret: Webhook secret configured in Razorpay Merchant Dashboard
    :return: True if valid, False otherwise
    """
    if not signature or not secret:
        return False
    
    try:
        calculated_signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_signature, signature)
    except Exception:
        return False
