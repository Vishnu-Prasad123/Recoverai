from typing import Dict, List
from pydantic import BaseModel

class MetricsOverviewResponse(BaseModel):
    total_failed_payments: int
    total_revenue_at_risk: float
    total_payments_count: int
    average_payment_amount: float
    ground_truth_recovered_revenue: float
    ground_truth_recovery_rate: float
    payment_count_by_failure_reason: Dict[str, int]
    payment_count_by_payment_method: Dict[str, int]

class FailureReasonMetric(BaseModel):
    failure_reason: str
    count: int
    total_revenue_at_risk: float
    recovery_rate: float
    recovered_count: int

class PaymentMethodMetric(BaseModel):
    payment_method: str
    count: int
    total_revenue_at_risk: float
    recovery_rate: float
    recovered_count: int
