"""
RecoverAI - Exploratory Dataset Analysis Module
Calculates dataset metrics, distributions, failure codes, and ground-truth recovery statistics.
"""

import os
import pandas as pd

def analyze_dataset(payments_csv: str = "data/payments.csv", customers_csv: str = "data/customers.csv"):
    if not os.path.exists(payments_csv):
        raise FileNotFoundError(f"File not found: '{payments_csv}'. Please generate dataset first.")

    df_payments = pd.read_csv(payments_csv)
    df_customers = pd.read_csv(customers_csv) if os.path.exists(customers_csv) else None

    total_payments = len(df_payments)
    total_customers = len(df_customers) if df_customers is not None else df_payments["customer_id"].nunique()
    
    total_revenue_at_risk = float(df_payments["amount"].sum())
    total_recovered_value = float(df_payments["amount_recovered"].sum())
    overall_recovery_rate = float(df_payments["recovered"].mean() * 100)
    avg_payment_amount = float(df_payments["amount"].mean())

    # Distributions
    failure_distribution = df_payments["failure_reason"].value_counts().to_dict()
    method_distribution = df_payments["payment_method"].value_counts().to_dict()

    # Grouped Recovery Rates
    rec_by_reason = df_payments.groupby("failure_reason")["recovered"].mean().mul(100).round(2).to_dict()
    rec_by_method = df_payments.groupby("payment_method")["recovered"].mean().mul(100).round(2).to_dict()
    val_by_reason = df_payments.groupby("failure_reason")["amount"].sum().round(2).to_dict()

    stats = {
        "total_payments": total_payments,
        "total_customers": total_customers,
        "total_revenue_at_risk": total_revenue_at_risk,
        "total_recovered_value": total_recovered_value,
        "overall_recovery_rate": overall_recovery_rate,
        "avg_payment_amount": avg_payment_amount,
        "failure_reason_distribution": failure_distribution,
        "payment_method_distribution": method_distribution,
        "recovery_rate_by_failure_reason": rec_by_reason,
        "recovery_rate_by_payment_method": rec_by_method,
        "revenue_at_risk_by_failure_reason": val_by_reason,
    }

    print("=" * 60)
    print(" RECOVERAI - SYNTHETIC DATASET STATISTICAL REPORT ")
    print("=" * 60)
    print(f"Total Payments Generated        : {total_payments:,}")
    print(f"Total Unique Customers          : {total_customers:,}")
    print(f"Total Revenue at Risk           : INR {total_revenue_at_risk:,.2f}")
    print(f"Total Ground-Truth Recovered    : INR {total_recovered_value:,.2f}")
    print(f"Overall Recovery Rate           : {overall_recovery_rate:.2f}%")
    print(f"Average Payment Amount          : INR {avg_payment_amount:,.2f}")
    print("-" * 60)
    print("\n[Failure Reason Breakdown]")
    for reason, count in failure_distribution.items():
        rec_pct = rec_by_reason.get(reason, 0.0)
        val = val_by_reason.get(reason, 0.0)
        print(f" - {reason:<25}: {count:>4} payments ({count/total_payments*100:>5.1f}%) | Recovery: {rec_pct:>5.1f}% | Risk: INR {val:>10,}")

    print("\n[Payment Method Breakdown]")
    for method, count in method_distribution.items():
        rec_pct = rec_by_method.get(method, 0.0)
        print(f" - {method:<15}: {count:>4} payments ({count/total_payments*100:>5.1f}%) | Recovery: {rec_pct:>5.1f}%")

    print("=" * 60)
    return stats

if __name__ == "__main__":
    analyze_dataset()
