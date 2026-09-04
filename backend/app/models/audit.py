from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    log_id = Column(String(64), unique=True, index=True, nullable=False)
    payment_id = Column(String(64), ForeignKey("payments.payment_id"), nullable=False, index=True)
    customer_id = Column(String(64), ForeignKey("customers.customer_id"), nullable=False, index=True)

    event_type = Column(String(64), nullable=False, index=True)  # PAYMENT_FAILED, SCORE_CALCULATED, ACTION_PROPOSED, GUARDRAIL_CHECK, ACTION_EXECUTED, RECOVERY_SUCCESS, ACTION_BLOCKED
    actor = Column(String(32), default="SYSTEM", nullable=False)  # SYSTEM, AI_AGENT, GUARDRAIL, MERCHANT, RAZORPAY_WEBHOOK
    details = Column(Text, nullable=False)  # JSON string metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    payment = relationship("Payment", back_populates="audit_logs")
    customer = relationship("Customer", back_populates="audit_logs")
