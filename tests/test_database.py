import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Customer, Payment, RecoveryAttempt, RecoveryDecision, AuditLog

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_customer_creation(db_session):
    c = Customer(
        customer_id="cust_test01",
        name="Test Payer",
        email="testpayer@example.com",
        lifetime_value=15000.0,
        total_payments_count=10,
        successful_payments_count=8,
        success_rate=0.80
    )
    db_session.add(c)
    db_session.commit()

    retrieved = db_session.query(Customer).filter_by(customer_id="cust_test01").first()
    assert retrieved is not None
    assert retrieved.name == "Test Payer"
    assert retrieved.success_rate == 0.80

def test_payment_and_relationship(db_session):
    c = Customer(
        customer_id="cust_test02",
        name="John Doe",
        email="john@example.com",
        success_rate=0.90
    )
    db_session.add(c)
    db_session.commit()

    p = Payment(
        payment_id="pay_test01",
        customer_id="cust_test02",
        amount=4999.0,
        currency="INR",
        payment_method="upi",
        failure_reason="temporary_bank_error",
        timestamp=datetime.now(timezone.utc),
        recovered=True,
        amount_recovered=4999.0
    )
    db_session.add(p)
    db_session.commit()

    retrieved_p = db_session.query(Payment).filter_by(payment_id="pay_test01").first()
    assert retrieved_p is not None
    assert retrieved_p.amount == 4999.0
    assert retrieved_p.customer.name == "John Doe"
    assert len(retrieved_p.customer.payments) == 1

def test_audit_log(db_session):
    c = Customer(customer_id="cust_test03", name="Alice", email="alice@example.com")
    p = Payment(
        payment_id="pay_test02", customer_id="cust_test03", amount=1200.0,
        currency="INR", payment_method="card", failure_reason="3ds_timeout",
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add_all([c, p])
    db_session.commit()

    log = AuditLog(
        log_id="log_001",
        payment_id="pay_test02",
        customer_id="cust_test03",
        event_type="PAYMENT_FAILED",
        actor="SYSTEM",
        details='{"reason": "3ds_timeout"}'
    )
    db_session.add(log)
    db_session.commit()

    retrieved_log = db_session.query(AuditLog).filter_by(log_id="log_001").first()
    assert retrieved_log is not None
    assert retrieved_log.payment.amount == 1200.0
