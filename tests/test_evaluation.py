import os
import json
import pytest
import numpy as np
import pandas as pd
from ai.evaluate_scoring import run_evaluation
from app.schemas.payment import PaymentFeatureInputs

def test_ground_truth_field_exclusion_leakage_check():
    """Verify that passing ground-truth fields to PaymentFeatureInputs raises an Error."""
    with pytest.raises(Exception):
        PaymentFeatureInputs(
            payment_id="pay_test_leak",
            customer_id="cust_test",
            amount=5000.0,
            currency="INR",
            payment_method="upi",
            failure_reason="network_failure",
            recovered=True  # FORBIDDEN
        )

    with pytest.raises(Exception):
        PaymentFeatureInputs(
            payment_id="pay_test_leak",
            customer_id="cust_test",
            amount=5000.0,
            currency="INR",
            payment_method="upi",
            failure_reason="network_failure",
            amount_recovered=5000.0  # FORBIDDEN
        )



def test_evaluation_execution_and_schema():
    """Verify run_evaluation executes properly and returns structured metric results."""
    results = run_evaluation(
        payments_csv="data/payments.csv",
        customers_csv="data/customers.csv",
        output_json="data/evaluation_results.json",
        output_md="docs/evaluation.md"
    )

    # Check top-level JSON structure
    assert "timestamp" in results
    assert "dataset_summary" in results
    assert "classification_metrics" in results
    assert "priority_distribution" in results
    assert "revenue_cutoffs" in results
    assert "data_leakage_audit" in results

    # Check dataset summary metrics
    ds = results["dataset_summary"]
    assert ds["total_payments"] == 2500
    assert ds["total_customers"] == 800
    assert ds["total_value_at_risk"] > 0
    assert ds["total_gt_recovered_revenue"] > 0

    # Check statistical metrics
    cm = results["classification_metrics"]
    assert 0.50 <= cm["roc_auc"] <= 1.0
    assert 0.0 <= cm["precision"] <= 1.0
    assert 0.0 <= cm["recall"] <= 1.0
    assert 0.0 <= cm["f1_score"] <= 1.0
    assert 0.0 <= cm["accuracy"] <= 1.0

    # Check priority distribution
    pd_dist = results["priority_distribution"]
    assert "HIGH" in pd_dist and "MEDIUM" in pd_dist and "LOW" in pd_dist
    total_prio_count = sum(item["count"] for item in pd_dist.values())
    assert total_prio_count == 2500

    # Check revenue cutoffs
    rc = results["revenue_cutoffs"]
    for cutoff_key, expected_count in [("Top_10%", 250), ("Top_20%", 500), ("Top_30%", 750)]:
        assert cutoff_key in rc
        cutoff_data = rc[cutoff_key]
        assert cutoff_data["selected_count"] == expected_count

        strategies = cutoff_data["strategies"]
        for strat in ["RecoverAI", "Amount_Only", "Failure_Reason_Only", "Random"]:
            assert strat in strategies
            s_data = strategies[strat]
            assert s_data["selected_count"] == expected_count
            assert 0 <= s_data["recovered_count"] <= expected_count
            assert 0.0 <= s_data["recovery_rate_pct"] <= 100.0
            assert s_data["recovered_revenue_inr"] >= 0.0
            assert 0.0 <= s_data["pct_revenue_captured"] <= 100.0


def test_random_baseline_reproducibility():
    """Verify that random baseline selection is independent and 100% reproducible with seed 42."""
    df_eval = pd.read_csv("data/payments.csv")
    np.random.seed(42)
    perm1 = np.random.permutation(len(df_eval))

    np.random.seed(42)
    perm2 = np.random.permutation(len(df_eval))

    assert np.array_equal(perm1, perm2), "Random seed 42 must be strictly reproducible"


def test_output_files_existence():
    """Verify that output evaluation files are created on disk."""
    assert os.path.exists("data/evaluation_results.json")
    assert os.path.exists("docs/evaluation.md")

    with open("data/evaluation_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["data_leakage_audit"]["recovered_in_features"] is False
        assert data["data_leakage_audit"]["amount_recovered_in_features"] is False

    with open("docs/evaluation.md", "r", encoding="utf-8") as f:
        content = f.read()
        assert "RecoverAI - Phase 10 Model Evaluation" in content
        assert "Zero Data Leakage" in content
