import math
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.payment import Payment
from app.models.customer import Customer
from app.schemas.payment import PaymentFeatureInputs

class PaymentService:
    @staticmethod
    def get_payments(
        db: Session,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        failure_reason: Optional[str] = None,
        payment_method: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
    ) -> Tuple[List[Payment], int, int]:
        """
        Retrieves paginated and filtered payment records.
        Returns (payments_list, total_count, total_pages).
        """
        query = db.query(Payment)

        if status:
            query = query.filter(Payment.status == status.upper())
        if failure_reason:
            query = query.filter(Payment.failure_reason == failure_reason.lower())
        if payment_method:
            query = query.filter(Payment.payment_method == payment_method.lower())
        if min_amount is not None:
            query = query.filter(Payment.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Payment.amount <= max_amount)

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        offset = (page - 1) * page_size
        payments = query.order_by(Payment.timestamp.desc()).offset(offset).limit(page_size).all()

        return payments, total_count, total_pages

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: str) -> Optional[Payment]:
        """Fetches a single payment by payment_id."""
        return db.query(Payment).filter(Payment.payment_id == payment_id).first()

    @staticmethod
    def get_payment_feature_inputs(db: Session, payment_id: str) -> Optional[PaymentFeatureInputs]:
        """
        Extracts clean feature input model for future AI Decision Engine context.
        Guaranteed to contain ZERO ground-truth label fields.
        """
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            return None

        customer = db.query(Customer).filter(Customer.customer_id == payment.customer_id).first()
        
        return PaymentFeatureInputs(
            payment_id=payment.payment_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            failure_reason=payment.failure_reason,
            timestamp=payment.timestamp,
            previous_attempts=payment.previous_attempts,
            previous_recovery_attempts=payment.previous_recovery_attempts,
            time_since_failure_minutes=payment.time_since_failure_minutes,
            customer_success_rate=customer.success_rate if customer else 0.5,
            customer_lifetime_value=customer.lifetime_value if customer else 0.0,
            customer_previous_payments=customer.total_payments_count if customer else 0,
        )
