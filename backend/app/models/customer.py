from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    
    # Historical Behavior Metrics
    lifetime_value = Column(Float, default=0.0, nullable=False)
    total_payments_count = Column(Integer, default=0, nullable=False)
    successful_payments_count = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="customer")

    def __repr__(self):
        return f"<Customer(customer_id='{self.customer_id}', success_rate={self.success_rate:.2f})>"
