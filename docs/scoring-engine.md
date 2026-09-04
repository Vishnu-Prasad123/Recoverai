# RecoverAI — Recovery Scoring Engine Specifications

> **Razorpay Buildathon 2026** | Scoring Architecture & Revenue Evaluation Framework

This document defines the deterministic scoring methodology, calibrated probability mapping, operational priority tiers, merchant explanations, evaluation metrics, and data leakage safeguards for RecoverAI's **Recovery Scoring Engine**.

---

## 1. Core Principles

The Recovery Scoring Engine answers a single crucial question prior to action execution:
$$\text{"How recoverable is this failed payment?"}$$

It evaluates transaction attributes using pre-decision features **ONLY** (`PaymentFeatureInputs`), generating a standardized score ($0–100$), calibrated probability ($0.0–1.0$), Expected Recovery Value ($\text{Amount} \times \text{Probability}$), Priority Tier (`HIGH`, `MEDIUM`, `LOW`), and human-readable factor explanations.

---

## 2. Component Scoring Formula

The total raw score ($0–100$) is computed from 4 weighted pre-decision components minus attempt and time penalties:

$$\text{Raw Score} = \Big( \sum w_i \cdot C_i \Big) - \text{Penalty}_{\text{attempts}} - \text{Penalty}_{\text{time}}$$

| Component | Weight ($w_i$) | Description |
| :--- | :---: | :--- |
| **Failure Reason & Method** | **40%** | Base recovery score per failure reason (`network_failure`: 85, `temporary_bank_error`: 80, `account_blocked`: 5) + payment method adjustment (`upi`: $+5$, `card`: $0$, `netbanking`: $-3$, `emi`: $-5$). |
| **Customer History** | **30%** | Customer historical success rate $= \text{customer\_success\_rate} \times 100$. |
| **Attempt Fatigue** | **15%** | Penalty for prior interventions $= 12 \times \text{previous\_recovery\_attempts} + 6 \times \max(0, \text{previous\_attempts} - 1)$. |
| **Time Decay** | **15%** | Penalty for elapsed time since failure $= \min(25.0, (\text{minutes\_ago} / 10080.0) \times 25.0)$. |

---

## 3. Calibrated Probability Mapping

To map the 0–100 Recovery Score to a realistic calibrated probability $P \in [0.02, 0.95]$ that matches the dataset ground-truth recovery rate (~60.4%), a logistic sigmoid curve centered at midpoint $70.0$ is applied:

$$P(\text{Recovery}) = \text{clip}\left( \frac{1}{1 + e^{-0.075 \cdot (\text{Score} - 70.0)}}, \; 0.02, \; 0.95 \right)$$

---

## 4. Expected Recovery Value & Operational Priority Tiers

$$\text{Expected Recovery Value (EV)} = \text{Payment Amount} \times P(\text{Recovery})$$

Payments are classified into three operational priority tiers:

- **`HIGH` Priority** (~30.4% of dataset):
  - $(\text{EV} \ge \text{INR } 2,000 \text{ AND } P \ge 0.55)$ **OR** $(P \ge 0.80)$
- **`MEDIUM` Priority** (~48.3% of dataset):
  - $(\text{EV} \ge \text{INR } 500 \text{ AND } P \ge 0.35)$
- **`LOW` Priority** (~21.3% of dataset):
  - All remaining payments (low expected value or low recovery probability $P < 0.35$).

---

## 5. Explainable Factor Generator

Every score evaluation returns structured explanations for merchant transparency:

```json
{
  "payment_id": "pay_100001",
  "recovery_score": 82.5,
  "recovery_probability": 0.7186,
  "expected_recovery_value": 3593.0,
  "priority": "HIGH",
  "factors": [
    {
      "factor": "failure_reason",
      "impact": "positive",
      "weight": 0.40,
      "description": "Failure code 'temporary_bank_error' (via UPI) is typically transient and has strong recovery potential."
    },
    {
      "factor": "customer_history",
      "impact": "positive",
      "weight": 0.30,
      "description": "Customer has a strong payment history (85.0% successful)."
    }
  ]
}
```

---

## 6. Zero Data Leakage Safeguards

Ground-truth evaluation fields (`recovered`, `amount_recovered`, `true_recovery_probability`) are strictly prohibited from entering `score_payment()`. 

The scoring engine executes explicit runtime checks:
```python
forbidden_fields = {"recovered", "amount_recovered", "true_recovery_probability"}
if set(features_dict.keys()).intersection(forbidden_fields):
    raise ValueError("DATA LEAKAGE DETECTED!")
```
