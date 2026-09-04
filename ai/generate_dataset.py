"""
RecoverAI - Synthetic Dataset Generator
Generates realistic, reproducible failed payment records for Razorpay Buildathon 2026.
Features ground-truth outcome modeling, realistic noise, and strict feature separation to eliminate data leakage.
"""

import os
import argparse
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

# Baseline Probabilities per Failure Reason
FAILURE_REASON_BASE_PROB = {
    "network_failure": 0.82,
    "temporary_bank_error": 0.78,
    "authentication_failure": 0.75,
    "3ds_timeout": 0.72,
    "payment_method_issue": 0.52,
    "insufficient_funds": 0.42,
    "customer_abandonment": 0.22,
    "account_blocked": 0.02,
}

PAYMENT_METHOD_WEIGHTS = {
    "upi": 0.45,
    "card": 0.30,
    "netbanking": 0.15,
    "wallet": 0.06,
    "emi": 0.04,
}

PAYMENT_METHOD_PROB_ADJUSTMENT = {
    "upi": 0.05,
    "card": 0.00,
    "netbanking": -0.04,
    "wallet": 0.02,
    "emi": -0.06,
}

FIRST_NAMES = ["Aarav", "Aditi", "Ananya", "Dev", "Isha", "Kabir", "Meera", "Neha", "Rohan", "Siddharth", "Tanvi", "Vikram", "Yash", "Zoya", "Amit", "Priya", "Rahul", "Suresh", "Kavita", "Rajesh"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Patel", "Mehta", "Singh", "Kumar", "Rao", "Nair", "Joshi", "Chopra", "Reddy", "Bhat", "Deshmukh", "Kapoor"]

def generate_synthetic_dataset(num_records: int = 2500, num_customers: int = 800, seed: int = 42, output_dir: str = "data"):
    random.seed(seed)
    np.random.seed(seed)


    print(f"[Dataset Generator] Generating {num_records} payment failure records across {num_customers} customers (seed={seed})...")

    # 1. Generate Customers
    customers_data = []
    customer_ids = [f"cust_{i+1001:05d}" for i in range(num_customers)]
    
    for c_id in customer_ids:
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        name = f"{fname} {lname}"
        email = f"{fname.lower()}.{lname.lower()}{random.randint(10,99)}@example.com"
        phone = f"+9198{random.randint(10000000, 99999999)}"
        
        # Customer tiers: Frequent Good Payers (60%), Mixed (30%), High Risk (10%)
        tier_rand = random.random()
        if tier_rand < 0.60:
            success_rate = round(random.uniform(0.75, 0.98), 3)
            total_pmts = random.randint(5, 50)
        elif tier_rand < 0.90:
            success_rate = round(random.uniform(0.40, 0.74), 3)
            total_pmts = random.randint(2, 25)
        else:
            success_rate = round(random.uniform(0.05, 0.39), 3)
            total_pmts = random.randint(1, 10)
            
        successful_pmts = max(0, int(total_pmts * success_rate))
        avg_ticket = round(random.uniform(300, 8000), 2)
        ltv = round(successful_pmts * avg_ticket, 2)

        customers_data.append({
            "customer_id": c_id,
            "name": name,
            "email": email,
            "phone": phone,
            "lifetime_value": ltv,
            "total_payments_count": total_pmts,
            "successful_payments_count": successful_pmts,
            "success_rate": success_rate
        })
        
    df_customers = pd.DataFrame(customers_data)

    # 2. Generate Payments
    payments_data = []
    now = datetime.now(timezone.utc)
    
    failure_reasons = list(FAILURE_REASON_BASE_PROB.keys())
    failure_weights = [0.25, 0.20, 0.15, 0.12, 0.10, 0.10, 0.05, 0.03]
    
    methods = list(PAYMENT_METHOD_WEIGHTS.keys())
    method_weights = list(PAYMENT_METHOD_WEIGHTS.values())

    for i in range(num_records):
        payment_id = f"pay_{i+100001:06d}"
        cust = df_customers.iloc[i % num_customers]
        customer_id = cust["customer_id"]

        # Transaction details
        # Log-normal distribution for amounts (mostly ₹500–₹10,000, occasional high value ₹15,000–₹50,000)
        amount = round(float(np.random.lognormal(mean=7.6, sigma=0.8)), 2)
        amount = max(100.0, min(amount, 75000.0))

        payment_method = np.random.choice(methods, p=method_weights)
        failure_reason = np.random.choice(failure_reasons, p=failure_weights)
        
        # Time since failure (between 5 minutes and 7 days ago)
        minutes_ago = float(np.random.exponential(scale=1440))  # avg ~1 day
        minutes_ago = max(5.0, min(minutes_ago, 10080.0))  # cap at 7 days
        timestamp = (now - timedelta(minutes=minutes_ago)).isoformat()

        # Attempts & Fatigue
        prev_attempts = random.choices([1, 2, 3], weights=[0.70, 0.20, 0.10])[0]
        prev_recovery_attempts = random.choices([0, 1, 2], weights=[0.65, 0.25, 0.10])[0]

        # -------------------------------------------------------------
        # GROUND TRUTH PROBABILITY CALCULATION (Hidden Logic)
        # -------------------------------------------------------------
        base_prob = FAILURE_REASON_BASE_PROB[failure_reason]
        method_adj = PAYMENT_METHOD_PROB_ADJUSTMENT[payment_method]
        cust_adj = 0.30 * (cust["success_rate"] - 0.50)
        fatigue_penalty = -0.14 * prev_recovery_attempts
        attempt_penalty = -0.08 * (prev_attempts - 1)
        
        # Time decay penalty (older payments decay in recovery chance)
        time_decay = max(0.20, 1.0 - (minutes_ago / 10080.0) * 0.40)

        # Realistic random noise (+/- 0.05)
        noise = np.random.normal(0, 0.04)

        raw_true_prob = (base_prob + method_adj + cust_adj + fatigue_penalty + attempt_penalty + noise) * time_decay
        true_recovery_prob = round(float(np.clip(raw_true_prob, 0.01, 0.95)), 4)

        # Bernoulli Ground Truth Recovery Outcome
        recovered = bool(np.random.binomial(1, true_recovery_prob))
        amount_recovered = amount if recovered else 0.0
        
        status = "RECOVERED" if recovered else "FAILED"

        payments_data.append({
            "payment_id": payment_id,
            "customer_id": customer_id,
            "amount": amount,
            "currency": "INR",
            "payment_method": payment_method,
            "failure_reason": failure_reason,
            "timestamp": timestamp,
            "previous_attempts": prev_attempts,
            "previous_recovery_attempts": prev_recovery_attempts,
            "time_since_failure_minutes": round(minutes_ago, 1),
            "customer_success_rate": cust["success_rate"],
            "customer_lifetime_value": cust["lifetime_value"],
            "customer_previous_payments": cust["total_payments_count"],
            "status": status,
            # GROUND TRUTH EVALUATION FIELDS (Hidden from feature set)
            "true_recovery_probability": true_recovery_prob,
            "recovered": recovered,
            "amount_recovered": amount_recovered,
        })

    df_payments = pd.DataFrame(payments_data)

    # Save to CSV
    os.makedirs(output_dir, exist_ok=True)
    customers_path = os.path.join(output_dir, "customers.csv")
    payments_path = os.path.join(output_dir, "payments.csv")

    
    df_customers.to_csv(customers_path, index=False)
    df_payments.to_csv(payments_path, index=False)

    print(f"[Dataset Generator] Successfully generated {len(df_customers)} customers -> '{customers_path}'")
    print(f"[Dataset Generator] Successfully generated {len(df_payments)} payments -> '{payments_path}'")
    print(f"[Dataset Generator] Overall Ground-Truth Recovery Rate: {df_payments['recovered'].mean() * 100:.2f}%")
    print(f"[Dataset Generator] Total Value at Risk: INR {df_payments['amount'].sum():,.2f}")
    print(f"[Dataset Generator] Total Ground-Truth Recovered Value: INR {df_payments['amount_recovered'].sum():,.2f}")

    return df_customers, df_payments

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate RecoverAI Synthetic Payment Failure Dataset")
    parser.add_argument("--records", type=int, default=2500, help="Number of failed payment records to generate")
    parser.add_argument("--customers", type=int, default=800, help="Number of unique customer profiles")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for exact reproducibility")
    args = parser.parse_args()

    generate_synthetic_dataset(num_records=args.records, num_customers=args.customers, seed=args.seed)
