import os
import pandas as pd
import pytest
from ai.generate_dataset import generate_synthetic_dataset
from app.schemas.payment import PaymentFeatureInputs

def test_dataset_generation(tmp_path):
    # Generates in temporary directory to avoid overwriting production data/payments.csv
    df_customers, df_payments = generate_synthetic_dataset(num_records=1000, num_customers=300, seed=123, output_dir=str(tmp_path))

    
    # Requirement: At least 1,000 records
    assert len(df_payments) >= 1000
    assert len(df_customers) >= 300

    # ID Uniqueness
    assert df_payments["payment_id"].is_unique
    assert df_customers["customer_id"].is_unique

    # Valid values
    assert (df_payments["amount"] > 0).all()
    assert df_payments["currency"].eq("INR").all()
    assert df_payments["recovered"].isin([True, False]).all()
    assert ((df_payments["true_recovery_probability"] >= 0.0) & (df_payments["true_recovery_probability"] <= 1.0)).all()

def test_data_leakage_prevention():
    """
    CRITICAL TEST: Ensures PaymentFeatureInputs schema strictly excludes
    target ground-truth fields ('recovered', 'amount_recovered', 'true_recovery_probability').
    """
    schema_fields = set(PaymentFeatureInputs.model_fields.keys())
    
    forbidden_target_fields = {"recovered", "amount_recovered", "true_recovery_probability"}
    leakage_fields = schema_fields.intersection(forbidden_target_fields)
    
    assert len(leakage_fields) == 0, f"DATA LEAKAGE DETECTED! Feature input schema contains target outcome fields: {leakage_fields}"
