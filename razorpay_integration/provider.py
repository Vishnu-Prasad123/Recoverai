"""
RecoverAI - Razorpay Provider Abstraction
Implements Provider Pattern isolating Razorpay API calls behind an abstract interface.
Supports Mock Mode for zero-cost offline tests and Real Mode for Razorpay Sandbox Test API.
"""

import time
import uuid
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.app.schemas.razorpay import PaymentLinkCreateRequest, PaymentLinkResponse
from razorpay_integration.config import RAZORPAY_CONFIG, RazorpayConfig

class RazorpayProvider(ABC):
    """Abstract Base Class for Razorpay Integration Providers."""

    @abstractmethod
    def create_payment_link(self, req: PaymentLinkCreateRequest) -> PaymentLinkResponse:
        """Creates a Razorpay Payment Link."""
        pass

    @abstractmethod
    def fetch_payment_link(self, link_id: str) -> Optional[PaymentLinkResponse]:
        """Fetches status details for a Razorpay Payment Link."""
        pass


class MockRazorpayProvider(RazorpayProvider):
    """
    Deterministic Offline Mock Provider.
    Simulates Razorpay Payment Link creation, fetching, and status updates for local testing.
    Does NOT connect to external networks.
    """
    def __init__(self):
        self._links: Dict[str, PaymentLinkResponse] = {}

    def create_payment_link(self, req: PaymentLinkCreateRequest) -> PaymentLinkResponse:
        link_id = f"plink_mock_{uuid.uuid4().hex[:10]}"
        now_epoch = int(time.time())
        short_url = f"https://rzp.io/i/mock_{req.payment_id}"
        
        response = PaymentLinkResponse(
            id=link_id,
            entity="payment_link",
            amount=req.amount,
            currency=req.currency,
            status="created",
            short_url=short_url,
            customer_id=f"cust_{req.payment_id}",
            created_at=now_epoch
        )
        self._links[link_id] = response
        return response

    def fetch_payment_link(self, link_id: str) -> Optional[PaymentLinkResponse]:
        return self._links.get(link_id)

    def simulate_payment_paid(self, link_id: str) -> Optional[PaymentLinkResponse]:
        """Test helper to simulate customer completing payment link."""
        link = self._links.get(link_id)
        if link:
            link.status = "paid"
        return link


class RealRazorpayAdapter(RazorpayProvider):
    """
    Production Adapter for Razorpay Sandbox / Test Mode REST API.
    Uses HTTP Basic Authentication with RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.
    """
    def __init__(self, config: RazorpayConfig = RAZORPAY_CONFIG):
        self.config = config
        self.config.validate_test_credentials()
        self.auth = (self.config.RAZORPAY_KEY_ID, self.config.RAZORPAY_KEY_SECRET)

    def create_payment_link(self, req: PaymentLinkCreateRequest) -> PaymentLinkResponse:
        url = f"{self.config.API_BASE_URL}/payment_links"
        payload = {
            "amount": int(req.amount * 100),  # Razorpay expects amount in paise
            "currency": req.currency,
            "accept_partial": False,
            "description": req.description,
            "customer": {
                "name": req.customer_name or "Valued Customer",
                "email": req.customer_email or "customer@example.com",
                "contact": req.customer_contact or "+919876543210"
            },
            "notify": {
                "sms": True,
                "email": True
            },
            "reminder_enable": True,
            "notes": {
                "payment_id": req.payment_id,
                "system": "RecoverAI"
            }
        }
        if req.expire_by:
            payload["expire_by"] = req.expire_by

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload, auth=self.auth)
                res.raise_for_status()
                data = res.json()
                
                return PaymentLinkResponse(
                    id=data["id"],
                    entity=data.get("entity", "payment_link"),
                    amount=float(data["amount"]) / 100.0,
                    currency=data.get("currency", "INR"),
                    status=data.get("status", "created"),
                    short_url=data.get("short_url", ""),
                    customer_id=data.get("customer", {}).get("id"),
                    created_at=int(data.get("created_at", time.time()))
                )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Razorpay Test Mode API Error ({e.response.status_code}): {e.response.text}")
        except httpx.RequestError as e:
            raise RuntimeError(f"Razorpay Connection Timeout / Network Error: {str(e)}")

    def fetch_payment_link(self, link_id: str) -> Optional[PaymentLinkResponse]:
        url = f"{self.config.API_BASE_URL}/payment_links/{link_id}"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, auth=self.auth)
                if res.status_code == 404:
                    return None
                res.raise_for_status()
                data = res.json()
                
                return PaymentLinkResponse(
                    id=data["id"],
                    entity=data.get("entity", "payment_link"),
                    amount=float(data["amount"]) / 100.0,
                    currency=data.get("currency", "INR"),
                    status=data.get("status", "created"),
                    short_url=data.get("short_url", ""),
                    customer_id=data.get("customer", {}).get("id"),
                    created_at=int(data.get("created_at", time.time()))
                )
        except Exception as e:
            raise RuntimeError(f"Failed to fetch Razorpay Payment Link '{link_id}': {str(e)}")


def get_razorpay_provider(config: RazorpayConfig = RAZORPAY_CONFIG) -> RazorpayProvider:
    """Factory function returning the configured Razorpay provider."""
    if config.is_real_test_mode():
        return RealRazorpayAdapter(config=config)
    return MockRazorpayProvider()
