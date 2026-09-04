from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.decision import RecoveryAction
from app.schemas.guardrail import GuardrailStatus

class PaymentLinkCreateRequest(BaseModel):
    payment_id: str
    amount: float
    currency: str = "INR"
    description: str = "RecoverAI Revenue Recovery Payment"
    customer_name: Optional[str] = "Valued Customer"
    customer_email: Optional[str] = "customer@example.com"
    customer_contact: Optional[str] = "+919876543210"
    expire_by: Optional[int] = None  # Epoch timestamp (default: 24 hours from creation)


class PaymentLinkResponse(BaseModel):
    id: str  # e.g., plink_L1a2b3c4d5e6
    entity: str = "payment_link"
    amount: float
    currency: str = "INR"
    status: str = "created"  # created, paid, expired, cancelled
    short_url: str
    customer_id: Optional[str] = None
    created_at: int
    model_config = ConfigDict(from_attributes=True)


class WebhookPayload(BaseModel):
    entity: str = "event"
    account_id: Optional[str] = None
    event: str  # payment.link.paid, payment.link.expired, payment.failed
    contains: List[str] = Field(default_factory=list)
    payload: Dict[str, Any]
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class RecoveryExecutionResponse(BaseModel):
    payment_id: str
    guardrail_status: GuardrailStatus
    original_action: RecoveryAction
    final_action: RecoveryAction
    execution_status: str  # EXECUTED_SUCCESS, BLOCKED_BY_GUARDRAILS, ESCALATED_FOR_HUMAN_REVIEW, IDEMPOTENT_SKIPPED, FAILED
    payment_link: Optional[PaymentLinkResponse] = None
    audit_id: Optional[str] = None
    executed_at: str
    message: str
    
    model_config = ConfigDict(from_attributes=True)
