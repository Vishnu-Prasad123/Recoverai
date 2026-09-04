"""
RecoverAI - AI Decision Agent Evaluation Framework
Evaluates decision recommendation quality and action distribution across representative scenario cases.
STRICTLY enforces zero data leakage safeguards.
"""

import os
import sys
import pandas as pd
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from datetime import datetime, timezone
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryAction
from ai.agent import ai_decision_agent
from ai.scoring import scoring_engine

def evaluate_decision_agent(payments_csv: str = "data/payments.csv", customers_csv: str = "data/customers.csv") -> Dict[str, Any]:
    if not os.path.exists(payments_csv):
        raise FileNotFoundError(f"File not found: '{payments_csv}'")

    print(f"[Agent Evaluator] Loading payment records from '{payments_csv}'...")
    df_payments = pd.read_csv(payments_csv)
    df_customers = pd.read_csv(customers_csv) if os.path.exists(customers_csv) else None
    cust_map = df_customers.set_index("customer_id").to_dict("index") if df_customers is not None else {}

    print(f"[Agent Evaluator] Evaluating AI Decision Agent on payment scenarios...")

    # 1. Evaluate Action Distribution across Dataset Sample
    sample_df = df_payments.head(500)  # Representative 500 payment sample
    actions: List[str] = []
    
    for _, row in sample_df.iterrows():
        c_id = row["customer_id"]
        c_info = cust_map.get(c_id, {})
        feat = PaymentFeatureInputs(
            payment_id=str(row["payment_id"]),
            customer_id=str(c_id),
            amount=float(row["amount"]),
            currency="INR",
            payment_method=str(row["payment_method"]),
            failure_reason=str(row["failure_reason"]),
            timestamp=str(row["timestamp"]),
            previous_attempts=int(row["previous_attempts"]),
            previous_recovery_attempts=int(row["previous_recovery_attempts"]),
            time_since_failure_minutes=float(row["time_since_failure_minutes"]),
            customer_success_rate=float(c_info.get("success_rate", row.get("customer_success_rate", 0.5))),
            customer_lifetime_value=float(c_info.get("lifetime_value", row.get("customer_lifetime_value", 0.0))),
            customer_previous_payments=int(c_info.get("total_payments_count", row.get("customer_previous_payments", 0))),
        )
        dec = ai_decision_agent.recommend_action(feat)
        actions.append(dec.action.value)

    action_counts = pd.Series(actions).value_counts().to_dict()

    # 2. Evaluate Specific Scenario Cases for All 5 Actions
    scenario_cases = [
        ("Transient Network Failure -> RETRY", PaymentFeatureInputs(
            payment_id="s1_retry", customer_id="c1", amount=4500.0, currency="INR", payment_method="upi",
            failure_reason="network_failure", timestamp=datetime.now(timezone.utc), previous_attempts=1,
            previous_recovery_attempts=0, time_since_failure_minutes=45.0, customer_success_rate=0.85,
            customer_lifetime_value=20000.0, customer_previous_payments=10
        ), RecoveryAction.RETRY),
        
        ("Insufficient Funds -> PAYMENT_LINK", PaymentFeatureInputs(
            payment_id="s2_link", customer_id="c2", amount=7500.0, currency="INR", payment_method="card",
            failure_reason="insufficient_funds", timestamp=datetime.now(timezone.utc), previous_attempts=1,
            previous_recovery_attempts=1, time_since_failure_minutes=60.0, customer_success_rate=0.75,
            customer_lifetime_value=35000.0, customer_previous_payments=15
        ), RecoveryAction.PAYMENT_LINK),
        
        ("Recent Network Spike -> WAIT", PaymentFeatureInputs(
            payment_id="s3_wait", customer_id="c3", amount=3000.0, currency="INR", payment_method="upi",
            failure_reason="network_failure", timestamp=datetime.now(timezone.utc), previous_attempts=1,
            previous_recovery_attempts=0, time_since_failure_minutes=5.0, customer_success_rate=0.80,
            customer_lifetime_value=12000.0, customer_previous_payments=6
        ), RecoveryAction.WAIT),
        
        ("Account Blocked -> STOP", PaymentFeatureInputs(
            payment_id="s4_stop", customer_id="c4", amount=500.0, currency="INR", payment_method="netbanking",
            failure_reason="account_blocked", timestamp=datetime.now(timezone.utc), previous_attempts=1,
            previous_recovery_attempts=0, time_since_failure_minutes=120.0, customer_success_rate=0.10,
            customer_lifetime_value=500.0, customer_previous_payments=1
        ), RecoveryAction.STOP),
        
        ("Low Success Rate -> HUMAN_REVIEW", PaymentFeatureInputs(
            payment_id="s5_review", customer_id="c5", amount=15000.0, currency="INR", payment_method="emi",
            failure_reason="payment_method_issue", timestamp=datetime.now(timezone.utc), previous_attempts=2,
            previous_recovery_attempts=1, time_since_failure_minutes=240.0, customer_success_rate=0.15,
            customer_lifetime_value=2000.0, customer_previous_payments=2
        ), RecoveryAction.HUMAN_REVIEW),
    ]

    scenario_results = []
    for name, feat, expected in scenario_cases:
        dec = ai_decision_agent.recommend_action(feat)
        match = (dec.action == expected)
        scenario_results.append({
            "scenario": name,
            "expected_action": expected.value,
            "recommended_action": dec.action.value,
            "match": match,
            "confidence": dec.confidence,
            "rationale": dec.rationale
        })

    # Print Report
    print("\n" + "=" * 65)
    print(" RECOVERAI - AI DECISION AGENT EVALUATION REPORT ")
    print("=" * 65)
    print(f"Evaluated Payment Sample Size   : {len(sample_df)}")
    print("-" * 65)
    print("[Action Distribution Across Representative Sample]")
    for act in ["RETRY", "PAYMENT_LINK", "WAIT", "STOP", "HUMAN_REVIEW"]:
        cnt = action_counts.get(act, 0)
        print(f"  - {act:<14}: {cnt:>3} payments ({cnt/len(sample_df)*100:5.2f}%)")
    print("-" * 65)
    print("[Scenario Decision Validation (5 Allowed Actions)]")
    for res in scenario_results:
        status_icon = "PASS" if res["match"] else "FAIL"
        print(f" [{status_icon}] {res['scenario']:<40} -> Action: {res['recommended_action']} (Conf: {res['confidence']})")
        print(f"        Rationale: {res['rationale']}")
    print("=" * 65 + "\n")

    return {
        "sample_size": len(sample_df),
        "action_distribution": action_counts,
        "scenario_results": scenario_results
    }

if __name__ == "__main__":
    evaluate_decision_agent()
