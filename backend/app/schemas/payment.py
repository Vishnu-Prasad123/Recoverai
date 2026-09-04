from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field

class PaymentFeatureInputs(BaseModel):
    """
    Features available to future AI Decision Engine / Recovery Models.
    CRITICAL: Does NOT contain target outcome fields ('recovered', 'amount_recovered').
    """
    payment_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    payment_method: str
    failure_reason: str
    timestamp: Union[datetime, str]
    previous_attempts: int = 1
    previous_recovery_attempts: int = 0
    time_since_failure_minutes: float = 0.0
    status: Optional[str] = "FAILED"  # Operational status (FAILED, RECOVERED, CANCELLED, etc.)
    
    # Customer contextual features
    customer_success_rate: float = Field(ge=0.0, le=1.0)
    customer_lifetime_value: float = Field(ge=0.0)
    customer_previous_payments: int = Field(ge=0)
    model_config = ConfigDict(extra="forbid")


class PaymentRead(PaymentFeatureInputs):
    id: int
    recovery_score: Optional[float] = None
    recovery_probability: Optional[float] = None
    expected_recovery_value: Optional[float] = None
    
    # Ground truth (Evaluation only)
    recovered: bool
    amount_recovered: float
    
    created_at: Union[datetime, str]
    updated_at: Union[datetime, str]
    model_config = ConfigDict(from_attributes=True)


class PaginatedPaymentResponse(BaseModel):
    items: List[PaymentRead]
    total: int
    page: int
    page_size: int
    total_pages: int
