# RecoverAI — Dataset Specifications & Ground-Truth Methodology

> **Razorpay Buildathon 2026** | Dataset Generation & Feature Leakage Protection Guide

This document details the generation methodology, probabilistic ground-truth formula, dataset statistics, and feature classification rules implemented in `ai/generate_dataset.py`.

---

## Data Leakage Prevention Rules

To guarantee that RecoverAI's evaluation results are authentic and scientifically credible, features are strictly segregated into four explicit categories:

| Category | Description | Fields Included | Available to AI Agent? |
| :--- | :--- | :--- | :--- |
| **Input Payment Features** | Contextual attributes of the failed transaction | `payment_id`, `amount`, `currency`, `payment_method`, `failure_reason`, `timestamp`, `previous_attempts`, `previous_recovery_attempts`, `time_since_failure_minutes` | ✅ **YES** |
| **Historical Customer Features** | Historical behavior of the payer prior to current failure | `customer_id`, `customer_success_rate`, `customer_lifetime_value`, `customer_previous_payments` | ✅ **YES** |
| **Target Ground-Truth Outcome** | Hidden true outcome used **ONLY** for offline/online evaluation | `true_recovery_probability`, `recovered`, `amount_recovered` | ❌ **STRICTLY PROHIBITED** |
| **Post-Action Intervention Outputs** | Generated after recovery intervention is chosen & executed | `status`, `recovery_score`, `expected_recovery_value`, `attempt_id` | ❌ **PROHIBITED PRIOR TO ACTION** |

---

## Ground-Truth Recovery Formula

The synthetic dataset generates realistic outcomes using a multi-factor probabilistic function:

$$P_{\text{true}} = \text{clip}\Big( \big(P_{\text{base}} + \Delta_{\text{method}} + \Delta_{\text{cust}} - \text{Penalty}_{\text{fatigue}} - \text{Penalty}_{\text{attempts}} + \epsilon \big) \times \text{Decay}_{\text{time}}, \; 0.01, \; 0.95 \Big)$$

Where:
- $P_{\text{base}}$: Base probability per failure reason:
  - `network_failure`: 0.82
  - `temporary_bank_error`: 0.78
  - `authentication_failure`: 0.75
  - `3ds_timeout`: 0.72
  - `payment_method_issue`: 0.52
  - `insufficient_funds`: 0.42
  - `customer_abandonment`: 0.22
  - `account_blocked`: 0.02
- $\Delta_{\text{method}}$: Payment method adjustment (`upi`: $+0.05$, `card`: $0.00$, `netbanking`: $-0.04$, `wallet`: $+0.02$, `emi`: $-0.06$)
- $\Delta_{\text{cust}}$: Customer success rate weighting $= 0.30 \times (\text{customer\_success\_rate} - 0.50)$
- $\text{Penalty}_{\text{fatigue}}$: Fatigue penalty per prior recovery attempt $= 0.14 \times \text{previous\_recovery\_attempts}$
- $\text{Penalty}_{\text{attempts}}$: Attempt penalty $= 0.08 \times (\text{previous\_attempts} - 1)$
- $\text{Decay}_{\text{time}}$: Elapsed time decay $= \max(0.20, 1.0 - (\text{minutes\_ago} / 10080.0) \times 0.40)$
- $\epsilon \sim \mathcal{N}(0, 0.04^2)$: Gaussian random noise ensuring non-deterministic realistic variance.

The ground-truth outcome label is sampled as a Bernoulli trial:
$$\text{recovered} \sim \text{Bernoulli}(P_{\text{true}})$$
$$\text{amount\_recovered} = \begin{cases} \text{amount} & \text{if } \text{recovered} = \text{True} \\ 0.0 & \text{if } \text{recovered} = \text{False} \end{cases}$$

---

## Dataset Reproduction Command

To regenerate the exact synthetic dataset (2,500 payment records across 800 customers):

```bash
python ai/generate_dataset.py --records 2500 --customers 800 --seed 42
```
