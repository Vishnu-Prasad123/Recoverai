"""
RecoverAI - Database Seeder & Data Quality Engine
Populates SQLite database from CSV datasets and executes quality validation checks.
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, SessionLocal
from app.models import Customer, Payment

VALID_PAYMENT_METHODS = {"upi", "card", "netbanking", "wallet", "emi"}
VALID_FAILURE_REASONS = {
    "network_failure", "temporary_bank_error", "authentication_failure",
    "3ds_timeout", "payment_method_issue", "insufficient_funds",
    "customer_abandonment", "account_blocked"
}

def seed_database(data_dir: str = "data"):
    print("[Database Seeder] Initializing database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    customers_csv = os.path.join(data_dir, "customers.csv")
    payments_csv = os.path.join(data_dir, "payments.csv")

    if not os.path.exists(customers_csv) or not os.path.exists(payments_csv):
        raise FileNotFoundError(
            f"Dataset files not found in '{data_dir}/'. Please run 'python ai/generate_dataset.py' first."
        )

    print(f"[Database Seeder] Loading dataset from '{customers_csv}' and '{payments_csv}'...")
    df_customers = pd.read_csv(customers_csv)
    df_payments = pd.read_csv(payments_csv)

    # -------------------------------------------------------------
    # DATA QUALITY CHECKS & VALIDATIONS
    # -------------------------------------------------------------
    print("[Database Seeder] Running data quality assertions...")

    # Check 1: No Duplicate IDs
    assert df_customers["customer_id"].is_unique, "Quality Check Failed: Duplicate customer_id found in customers.csv"
    assert df_payments["payment_id"].is_unique, "Quality Check Failed: Duplicate payment_id found in payments.csv"

    # Check 2: Mandatory non-null keys
    assert not df_customers["customer_id"].isnull().any(), "Quality Check Failed: Null customer_id in customers.csv"
    assert not df_payments["payment_id"].isnull().any(), "Quality Check Failed: Null payment_id in payments.csv"
    assert not df_payments["amount"].isnull().any(), "Quality Check Failed: Null amount in payments.csv"

    # Check 3: Positive Amount
    assert (df_payments["amount"] > 0).all(), "Quality Check Failed: Payment amount <= 0 found"

    # Check 4: Valid Categorical Fields
    invalid_methods = set(df_payments["payment_method"]) - VALID_PAYMENT_METHODS
    assert len(invalid_methods) == 0, f"Quality Check Failed: Invalid payment methods found: {invalid_methods}"

    invalid_reasons = set(df_payments["failure_reason"]) - VALID_FAILURE_REASONS
    assert len(invalid_reasons) == 0, f"Quality Check Failed: Invalid failure reasons found: {invalid_reasons}"

    # Check 5: Bounds on rates & probabilities
    assert ((df_customers["success_rate"] >= 0.0) & (df_customers["success_rate"] <= 1.0)).all(), "Quality Check Failed: Invalid success_rate bounds"
    assert ((df_payments["true_recovery_probability"] >= 0.0) & (df_payments["true_recovery_probability"] <= 1.0)).all(), "Quality Check Failed: Invalid recovery probability bounds"

    print("[Database Seeder] Data quality checks PASSED cleanly!")

    # -------------------------------------------------------------
    # DB SEEDING
    # -------------------------------------------------------------
    db: Session = SessionLocal()
    try:
        # Seed Customers
        customer_objs = []
        for _, row in df_customers.iterrows():
            c = Customer(
                customer_id=row["customer_id"],
                name=row["name"],
                email=row["email"],
                phone=row["phone"],
                lifetime_value=float(row["lifetime_value"]),
                total_payments_count=int(row["total_payments_count"]),
                successful_payments_count=int(row["successful_payments_count"]),
                success_rate=float(row["success_rate"])
            )
            customer_objs.append(c)
        
        db.bulk_save_objects(customer_objs)
        db.commit()
        print(f"[Database Seeder] Successfully inserted {len(customer_objs)} Customer records into database.")

        # Seed Payments
        payment_objs = []
        for _, row in df_payments.iterrows():
            ts = datetime.fromisoformat(row["timestamp"])
            p = Payment(
                payment_id=row["payment_id"],
                customer_id=row["customer_id"],
                amount=float(row["amount"]),
                currency=row["currency"],
                payment_method=row["payment_method"],
                failure_reason=row["failure_reason"],
                timestamp=ts,
                previous_attempts=int(row["previous_attempts"]),
                previous_recovery_attempts=int(row["previous_recovery_attempts"]),
                time_since_failure_minutes=float(row["time_since_failure_minutes"]),
                status=row["status"],
                recovered=bool(row["recovered"]),
                amount_recovered=float(row["amount_recovered"])
            )
            payment_objs.append(p)

        db.bulk_save_objects(payment_objs)
        db.commit()
        print(f"[Database Seeder] Successfully inserted {len(payment_objs)} Payment records into database.")

    except Exception as e:
        db.rollback()
        print(f"[Database Seeder] Error seeding database: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
