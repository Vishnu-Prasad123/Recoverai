from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(String(64), unique=True, index=True, nullable=False)
    payment_id = Column(String(64), ForeignKey("payments.payment_id"), nullable=False, index=True)

    attempt_number = Column(Integer, nullable=False)
    action_type = Column(String(32), nullable=False)  # RETRY, PAYMENT_LINK, WAIT, STOP, HUMAN_REVIEW
    status = Column(String(32), nullable=False)  # SUCCESS, FAILED, PENDING, BLOCKED
    
    response_payload = Column(Text, nullable=True)  # JSON payload string from Razorpay or simulator
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    payment = relationship("Payment", back_populates="recovery_attempts")


class RecoveryDecision(Base):
    __tablename__ = "recovery_decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    decision_id = Column(String(64), unique=True, index=True, nullable=False)
    payment_id = Column(String(64), ForeignKey("payments.payment_id"), nullable=False, index=True)

    recovery_score = Column(Float, nullable=False)
    recovery_probability = Column(Float, nullable=False)
    expected_recovery_value = Column(Float, nullable=False)
    
    proposed_action = Column(String(32), nullable=False)  # RETRY, PAYMENT_LINK, WAIT, STOP, HUMAN_REVIEW
    guardrail_status = Column(String(32), nullable=False)  # ALLOWED, MODIFIED, BLOCKED
    executed_action = Column(String(32), nullable=False)
    
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    reasoning_summary = Column(Text, nullable=False)  # Bulleted explanation for merchants
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    payment = relationship("Payment", back_populates="recovery_decisions")
