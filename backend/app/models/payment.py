from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payment_id = Column(String(64), unique=True, index=True, nullable=False)
    customer_id = Column(String(64), ForeignKey("customers.customer_id"), nullable=False, index=True)

    # Core Payment Features
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    payment_method = Column(String(32), nullable=False, index=True)  # upi, card, netbanking, wallet, emi
    failure_reason = Column(String(64), nullable=False, index=True)  # temporary_bank_error, insufficient_funds, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # State & Attempt Counters
    previous_attempts = Column(Integer, default=1, nullable=False)
    previous_recovery_attempts = Column(Integer, default=0, nullable=False)
    time_since_failure_minutes = Column(Float, default=0.0, nullable=False)
    status = Column(String(32), default="FAILED", nullable=False, index=True)  # FAILED, RECOVERED, STOPPED, PENDING

    # Scores & Decisions (Populated during recovery workflow)
    recovery_score = Column(Float, nullable=True)  # 0 to 100
    recovery_probability = Column(Float, nullable=True)  # 0.0 to 1.0
    expected_recovery_value = Column(Float, nullable=True)  # amount * probability

    # GROUND TRUTH OUTCOME (For evaluation only - NOT used as prediction features)
    recovered = Column(Boolean, default=False, nullable=False)
    amount_recovered = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="payments")
    recovery_attempts = relationship("RecoveryAttempt", back_populates="payment", cascade="all, delete-orphan")
    recovery_decisions = relationship("RecoveryDecision", back_populates="payment", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="payment", cascade="all, delete-orphan")

    @property
    def customer_success_rate(self) -> float:
        return self.customer.success_rate if self.customer else 0.5

    @property
    def customer_lifetime_value(self) -> float:
        return self.customer.lifetime_value if self.customer else 0.0

    @property
    def customer_previous_payments(self) -> int:
        return self.customer.total_payments_count if self.customer else 0

    def __repr__(self):
        return f"<Payment(payment_id='{self.payment_id}', amount={self.amount}, status='{self.status}')>"
