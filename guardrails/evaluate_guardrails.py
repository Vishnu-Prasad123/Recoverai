"""
RecoverAI - Guardrail Engine Evaluation Framework
Evaluates Independent Guardrail Safety Engine across dataset samples and scenario cases.
Measures ALLOW, MODIFY, and BLOCK status distributions and triggered rule statistics.
"""

import os
import sys
import pandas as pd
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from datetime import datetime, timezone
from app.schemas.payment import PaymentFeatureInputs
from app.schemas.decision import RecoveryDecision, RecoveryAction
from app.schemas.guardrail import GuardrailStatus
from ai.agent import ai_decision_agent
from guardrails.engine import guardrail_engine

def evaluate_guardrails_engine(payments_csv: str = "data/payments.csv", customers_csv: str = "data/customers.csv") -> Dict[str, Any]:
    if not os.path.exists(payments_csv):
        raise FileNotFoundError(f"File not found: '{payments_csv}'")

    print(f"[Guardrail Evaluator] Loading payment records from '{payments_csv}'...")
    df_payments = pd.read_csv(payments_csv)
    df_customers = pd.read_csv(customers_csv) if os.path.exists(customers_csv) else None
    cust_map = df_customers.set_index("customer_id").to_dict("index") if df_customers is not None else {}

    print(f"[Guardrail Evaluator] Evaluating Guardrail Engine on payment dataset sample...")

    # 1. Evaluate Guardrail Status Distribution over 500 Payment Sample
    sample_df = df_payments.head(500)
    statuses: List[str] = []
    triggered_rules_all: List[str] = []

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
        proposed_decision = ai_decision_agent.recommend_action(feat)
        g_result = guardrail_engine.evaluate_decision(features=feat, decision=proposed_decision)

        statuses.append(g_result.status.value)
        triggered_rules_all.extend(g_result.rules_triggered)

    status_counts = pd.Series(statuses).value_counts().to_dict()
    rule_counts = pd.Series(triggered_rules_all).value_counts().to_dict() if triggered_rules_all else {}

    # 2. Evaluate Specific Test Scenarios (ALLOW, MODIFY, BLOCK)
    scenarios = [
        ("Valid Transient Payment -> ALLOW", PaymentFeatureInputs(
            payment_id="g1_allow", customer_id="c1", amount=5000.0, currency="INR", payment_method="upi",
            failure_reason="temporary_bank_error", timestamp=datetime.now(timezone.utc), previous_attempts=1,
            previous_recovery_attempts=0, time_since_failure_minutes=30.0, customer_success_rate=0.85,
            customer_lifetime_value=25000.0, customer_previous_payments=10
        ), RecoveryDecision(
            payment_id="g1_allow", action=RecoveryAction.RETRY, confidence=0.88, rationale="Retry transient error",
            expected_recovery_value=3500.0, priority="HIGH", recommended_delay_minutes=0, risk_level="LOW"
        ), GuardrailStatus.ALLOW),

        ("High-Value Payment (INR 35,000) -> MODIFY to HUMAN_REVIEW", PaymentFeatureInputs(
            payment_id="g2_modify", customer_id="c2", amount=35000.0, currency="INR", payment_method="card",
            failure_reason="insufficient_funds", timestamp=datetime.now(timezone.utc), previous_attempts=1,
            previous_recovery_attempts=0, time_since_failure_minutes=60.0, customer_success_rate=0.80,
            customer_lifetime_value=50000.0, customer_previous_payments=20
        ), RecoveryDecision(
            payment_id="g2_modify", action=RecoveryAction.PAYMENT_LINK, confidence=0.85, rationale="Send link",
            expected_recovery_value=24500.0, priority="HIGH", recommended_delay_minutes=0, risk_level="LOW"
        ), GuardrailStatus.MODIFY),

        ("Max Recovery Attempts Reached (2 Attempts) -> BLOCK", PaymentFeatureInputs(
            payment_id="g3_block_attempts", customer_id="c3", amount=4000.0, currency="INR", payment_method="upi",
            failure_reason="network_failure", timestamp=datetime.now(timezone.utc), previous_attempts=2,
            previous_recovery_attempts=2, time_since_failure_minutes=120.0, customer_success_rate=0.70,
            customer_lifetime_value=15000.0, customer_previous_payments=8
        ), RecoveryDecision(
            payment_id="g3_block_attempts", action=RecoveryAction.RETRY, confidence=0.85, rationale="Retry network error",
            expected_recovery_value=2800.0, priority="MEDIUM", recommended_delay_minutes=0, risk_level="LOW"
        ), GuardrailStatus.BLOCK),

        ("Already Recovered Operational State -> BLOCK", PaymentFeatureInputs(
            payment_id="g4_block_state", customer_id="c4", amount=6000.0, currency="INR", payment_method="card",
            failure_reason="temporary_bank_error", timestamp=datetime.now(timezone.utc), previous_attempts=1,
            previous_recovery_attempts=0, time_since_failure_minutes=30.0, customer_success_rate=0.80,
            customer_lifetime_value=20000.0, customer_previous_payments=10, status="RECOVERED"
        ), RecoveryDecision(
            payment_id="g4_block_state", action=RecoveryAction.RETRY, confidence=0.90, rationale="Retry",
            expected_recovery_value=4200.0, priority="HIGH", recommended_delay_minutes=0, risk_level="LOW"
        ), GuardrailStatus.BLOCK),
    ]

    scenario_results = []
    for name, feat, prop_dec, expected_status in scenarios:
        res = guardrail_engine.evaluate_decision(features=feat, decision=prop_dec)
        match = (res.status == expected_status)
        scenario_results.append({
            "scenario": name,
            "expected_status": expected_status.value,
            "actual_status": res.status.value,
            "match": match,
            "original_action": res.original_action.value,
            "final_action": res.final_action.value,
            "reason": res.reason
        })

    # Print Report
    print("\n" + "=" * 65)
    print(" RECOVERAI - INDEPENDENT GUARDRAIL ENGINE EVALUATION REPORT ")
    print("=" * 65)
    print(f"Evaluated Sample Size           : {len(sample_df)}")
    print("-" * 65)
    print("[Guardrail Status Distribution across Representative Sample]")
    for st in ["ALLOW", "MODIFY", "BLOCK"]:
        cnt = status_counts.get(st, 0)
        print(f"  - {st:<10}: {cnt:>3} payments ({cnt/len(sample_df)*100:5.2f}%)")
    print("-" * 65)
    print("[Triggered Safety Rule Frequency]")
    if rule_counts:
        for r_id, count in rule_counts.items():
            print(f"  * {r_id:<25}: {count:>3} times")
    else:
        print("  * No blocking rules triggered in sample.")
    print("-" * 65)
    print("[Scenario Decision Validation (ALLOW, MODIFY, BLOCK)]")
    for s_res in scenario_results:
        status_icon = "PASS" if s_res["match"] else "FAIL"
        print(f" [{status_icon}] {s_res['scenario']}")
        print(f"        Status: {s_res['actual_status']} | Action: {s_res['original_action']} -> {s_res['final_action']}")
        print(f"        Reason: {s_res['reason']}")
    print("=" * 65 + "\n")

    return {
        "sample_size": len(sample_df),
        "status_distribution": status_counts,
        "triggered_rules": rule_counts,
        "scenario_results": scenario_results
    }

if __name__ == "__main__":
    evaluate_guardrails_engine()
