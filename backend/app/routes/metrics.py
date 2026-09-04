from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.metrics_service import MetricsService
from app.schemas.metrics import MetricsOverviewResponse, FailureReasonMetric, PaymentMethodMetric

router = APIRouter(prefix="/api/metrics", tags=["Metrics API"])

@router.get("/overview", response_model=MetricsOverviewResponse)
def get_metrics_overview(db: Session = Depends(get_db)):
    """
    Retrieves macro summary metrics: total failed payments, revenue at risk,
    average payment amount, and failure/method distributions.
    """
    return MetricsService.get_metrics_overview(db)

@router.get("/failure-reasons", response_model=List[FailureReasonMetric])
def get_failure_reason_metrics(db: Session = Depends(get_db)):
    """
    Retrieves payment failure breakdown metrics grouped by failure_reason.
    """
    return MetricsService.get_failure_reason_metrics(db)

@router.get("/payment-methods", response_model=List[PaymentMethodMetric])
def get_payment_method_metrics(db: Session = Depends(get_db)):
    """
    Retrieves payment breakdown metrics grouped by payment_method.
    """
    return MetricsService.get_payment_method_metrics(db)
