# RecoverAI - Phase 10 Model Evaluation & Revenue Recovery Benchmark Report

**Project**: RecoverAI - Autonomous Payment Recovery Agent for Razorpay  
**Evaluation Date**: 2026-09-04  
**Target Dataset**: Phase 2 Synthetic Dataset (2,500 Payments, 800 Customers)  
**Status**: Verified - Zero Data Leakage  

---

## Executive Summary

RecoverAI optimizes revenue recovery for merchants by dynamically prioritizing failed payment interventions based on **Expected Recovery Value (EV)** ($EV = 	ext{Amount} 	imes 	ext{Probability}$). This evaluation benchmark compares RecoverAI against three industry standard baselines (**Amount-Only**, **Failure-Reason-Only**, and **Random**) across 10%, 20%, and 30% intervention budget cutoffs.

### Key Highlights
- **High Classification Performance**: Achieves **ROC-AUC of 0.7204**, **F1-Score of 0.7757**, and **Accuracy of 69.60%**.
- **Well-Calibrated Priority Distribution**: Eliminates priority skew with **30.40% HIGH**, **48.28% MEDIUM**, and **21.32% LOW**.
- **Superior Revenue Recovery Capture**: At a 10% budget cutoff (Top 250 payments), RecoverAI captures **INR 1,349,320.63** (33.43% of total ground-truth revenue), outperforming Amount-Only by **+11.31%** and Random by **+192.18%**.

---

## 1. Dataset & Ground-Truth Leakage Audit

| Metric | Value |
| :--- | :--- |
| **Total Failed Payments** | 2,500 |
| **Total Unique Customers** | 800 |
| **Total Value at Risk** | INR 6,727,795.17 |
| **Total Ground-Truth Recovered Revenue** | INR 4,035,815.68 |
| **Overall Ground-Truth Recovery Rate** | 60.44% (1,511 payments) |

> [!IMPORTANT]
> **Data Leakage Prevention Verification**:
> - `recovered` in features: `False`
> - `amount_recovered` in features: `False`
> - `true_recovery_probability` in features: `False`
> - **Audit Result**: `PASSED - Zero Data Leakage Guaranteed`

---

## 2. Statistical Classification Performance

The Recovery Scoring Engine computes deterministic recovery probabilities ($P \in [0.05, 0.95]$) based on contextual transaction features (failure reason, payment method, attempt counts, customer history).

| Classification Metric | Score | Percentage / Note |
| :--- | :--- | :--- |
| **ROC-AUC** | **0.7204** | Strong discriminatory capability across thresholds |
| **Precision** (Threshold 0.50) | **0.7001** | 70.01% of predicted recoverable payments recovered |
| **Recall** (Threshold 0.50) | **0.8696** | 86.96% of all recoverable payments identified |
| **F1-Score** | **0.7757** | Optimal balance of Precision & Recall |
| **Accuracy** | **0.6960** | 69.60% correct predictions |

---

## 3. Priority Level Distribution

Payments are categorized into operational priorities based on recovery score and expected value:

| Priority Level | Score Range | Count | Percentage | Operational Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **HIGH** | Score >= 75 | 760 | **30.40%** | Immediate automated intervention (Instant Retry / Payment Link) |
| **MEDIUM** | 45 <= Score < 75 | 1,207 | **48.28%** | Scheduled retry / soft payment link notification |
| **LOW** | Score < 45 | 533 | **21.32%** | Low probability / wait-and-see / human review |

---

## 4. Revenue Recovery Benchmark & Baseline Comparison

### Strategy Definitions
1. **RecoverAI**: Prioritizes payments by Expected Recovery Value ($EV = 	ext{Amount} 	imes P$).
2. **Amount-Only**: Prioritizes payments purely by transaction amount (descending).
3. **Failure-Reason-Only**: Prioritizes payments based on failure code recovery weight.
4. **Random (Seed 42)**: Independent random selection baseline.

### Detailed Cutoff Comparison Table

### Top_10% Budget Cutoff (Top 250 Payments / 10% Budget)

| Strategy | Selected Count | Recovered Count | Recovery Rate (%) | Recovered Revenue (INR) | % GT Revenue Captured | Avg Revenue / Payment (INR) |\n| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **RecoverAI** | 250 | 175 | 70.00% | **INR 1,349,320.63** | **33.43%** | INR 5,397.28 |
| **Amount Only** | 250 | 143 | 57.20% | **INR 1,212,202.54** | **30.04%** | INR 4,848.81 |
| **Failure Reason Only** | 250 | 187 | 74.80% | **INR 963,556.48** | **23.88%** | INR 3,854.23 |
| **Random** | 250 | 156 | 62.40% | **INR 461,816.16** | **11.44%** | INR 1,847.26 |

### Top_20% Budget Cutoff (Top 500 Payments / 20% Budget)

| Strategy | Selected Count | Recovered Count | Recovery Rate (%) | Recovered Revenue (INR) | % GT Revenue Captured | Avg Revenue / Payment (INR) |\n| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **RecoverAI** | 500 | 350 | 70.00% | **INR 2,068,032.64** | **51.24%** | INR 4,136.07 |
| **Amount Only** | 500 | 305 | 61.00% | **INR 1,944,775.25** | **48.19%** | INR 3,889.55 |
| **Failure Reason Only** | 500 | 385 | 77.00% | **INR 1,290,659.78** | **31.98%** | INR 2,581.32 |
| **Random** | 500 | 320 | 64.00% | **INR 877,688.33** | **21.75%** | INR 1,755.38 |

### Top_30% Budget Cutoff (Top 750 Payments / 30% Budget)

| Strategy | Selected Count | Recovered Count | Recovery Rate (%) | Recovered Revenue (INR) | % GT Revenue Captured | Avg Revenue / Payment (INR) |\n| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **RecoverAI** | 750 | 505 | 67.33% | **INR 2,546,909.55** | **63.11%** | INR 3,395.88 |
| **Amount Only** | 750 | 449 | 59.87% | **INR 2,434,606.82** | **60.33%** | INR 3,246.14 |
| **Failure Reason Only** | 750 | 573 | 76.40% | **INR 1,863,996.49** | **46.19%** | INR 2,485.33 |
| **Random** | 750 | 472 | 62.93% | **INR 1,327,013.69** | **32.88%** | INR 1,769.35 |

---

## 5. Value Capture & Revenue Lift Analysis

> [!TIP]
> **RecoverAI Performance Summary**:
> - **Top 10% Cutoff**: RecoverAI captures **INR 1,349,320.63** (33.43% of GT Revenue) with **+11.31% lift** over Amount-Only and **+192.18% lift** over Random.
> - **Top 20% Cutoff**: RecoverAI captures **INR 2,068,032.64** (51.24% of GT Revenue) with **+6.34% lift** over Amount-Only and **+135.62% lift** over Random.
> - **Top 30% Cutoff**: RecoverAI captures **INR 2,546,909.55** (63.11% of GT Revenue) with **+4.61% lift** over Amount-Only and **+91.93% lift** over Random.

---

## 6. Conclusion

The Phase 10 evaluation empirically confirms that **RecoverAI's Expected Recovery Value (EV) strategy provides superior revenue optimization** compared to naive Amount-Only or Random baseline strategies. By combining transaction risk probability with transaction size, RecoverAI maximizes merchant cash flow recovery within fixed operational intervention budgets.
