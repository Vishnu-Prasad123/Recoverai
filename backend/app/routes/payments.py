from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.payment_service import PaymentService
from app.schemas.payment import PaymentRead, PaginatedPaymentResponse

router = APIRouter(prefix="/api/payments", tags=["Payments API"])

@router.get("", response_model=PaginatedPaymentResponse)
def get_payments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. FAILED, RECOVERED, STOPPED)"),
    failure_reason: Optional[str] = Query(None, description="Filter by failure reason code"),
    payment_method: Optional[str] = Query(None, description="Filter by payment method"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum transaction amount"),
    db: Session = Depends(get_db)
):
    """
    Retrieves paginated list of payment failure records with optional filtering.
    """
    items, total, total_pages = PaymentService.get_payments(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        failure_reason=failure_reason,
        payment_method=payment_method,
        min_amount=min_amount,
        max_amount=max_amount
    )

    return PaginatedPaymentResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment_detail(payment_id: str, db: Session = Depends(get_db)):
    """
    Retrieves detailed transaction information for a specific payment.
    Returns HTTP 404 if payment is not found.
    """
    payment = PaymentService.get_payment_by_id(db, payment_id=payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment not found with ID '{payment_id}'"
        )
    return payment
