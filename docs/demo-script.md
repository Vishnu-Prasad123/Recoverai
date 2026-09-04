# RecoverAI — 5-Minute Buildathon Video / Live Demonstration Script

**Track**: AI for Digital Commerce & Payments / Razorpay Buildathon 2026  
**Product**: RecoverAI — Guardrail-Controlled Revenue Recovery Agent  
**Target Duration**: ~5 Minutes (300 seconds)  

---

## Executive Positioning Statement

> *"RecoverAI is an AI-powered revenue recovery agent for failed payments. It ranks revenue at risk using Expected Recovery Value, recommends bounded recovery actions, enforces independent safety guardrails, executes approved workflows through Razorpay Test Mode, verifies outcomes through webhooks, and maintains an auditable recovery trail."*

---

## Timeline & Talking Points Breakdown

```
[0:00 - 0:30]  01. THE PROBLEM (Revenue Leakage in Digital Commerce)
[0:30 - 1:00]  02. THE SOLUTION (Expected Recovery Value Prioritization)
[1:00 - 2:00]  03. OPERATIONAL MERCHANT DASHBOARD
[2:00 - 3:20]  04. LIVE RECOVERY WORKFLOW (Successful Path: ALLOW)
[3:20 - 4:20]  05. INDEPENDENT GUARDRAIL SAFETY (Blocked Path: BLOCK)
[4:20 - 5:00]  06. QUANTITATIVE BENCHMARK EVALUATION & CONCLUSION
```

---

### [0:00 – 0:30] Stage 1: The Problem — Revenue Leakage in Digital Commerce

**Visual**: Screen showing failed payments in merchant dashboard / Razorpay webhook logs.  
**Speaker Notes**:
> *"Every day, online merchants process thousands of transactions. Up to 15% of payment attempts fail due to temporary network errors, 3DS timeouts, or payment method issues. Traditional recovery approaches either spam every customer with retries or blindly sort failures by payment amount. This leads to customer friction, wasted retry budgets, and lost revenue."*

---

### [0:30 – 1:00] Stage 2: The Solution — Expected Recovery Value ($EV$)

**Visual**: Slide / Diagram showing $EV = \text{Amount} \times P(\text{Recovery})$.  
**Speaker Notes**:
> *"Enter **RecoverAI**. Instead of treating all failed payments equally, RecoverAI predicts the exact recovery probability ($P$) for each failure based on 13 transaction and customer features. It multiplies this probability by transaction amount to calculate the **Expected Recovery Value ($EV$)**. Merchants can now prioritize interventions where expected cash recovery is highest."*

---

### [1:00 – 2:00] Stage 3: Merchant Dashboard & Executive Metrics

**Visual**: Live walkthrough of RecoverAI Web UI (`http://localhost:5173`).  
**Speaker Notes**:
> *"Here is the RecoverAI Merchant Dashboard. In real-time, merchants see total Revenue at Risk, Expected Recoverable Revenue, verified Actual Recovered Revenue, and the operational Recovery Queue. Each payment card displays transaction amount, failure reason, recovery score, priority tier, proposed AI action, guardrail state, and current status."*

---

### [2:00 – 3:20] Stage 4: Live Recovery Execution (Scenario A: Allowed Payment)

**Visual**: Click on payment `pay_100003` in UI, or run CLI script `python scripts/demo_pipeline.py pay_100003`.  
**Speaker Notes**:
> *"Let's trace a live recovery flow for payment `pay_100003` (₹4,500 via UPI due to 3DS authentication failure):*
> 1. **Scoring Engine**: Evaluates features and assigns Score `77.1/100`, Probability `62.99%`, EV `₹2,834.55` (HIGH Priority).
> 2. **AI Decision Agent**: Recommends `PAYMENT_LINK` based on failure type and customer history.
> 3. **Independent Guardrail Engine**: Evaluates 8 deterministic safety rules. Result: `ALLOW`.
> 4. **Razorpay Execution**: Creates a Razorpay Test Mode Payment Link (`https://rzp.io/i/...`).
> 5. **Webhook Verification**: Verifies incoming `payment.link.paid` webhook signature (HMAC-SHA256). Status updates to **`RECOVERED`** and logs an immutable audit trail."*

---

### [3:20 – 4:20] Stage 5: Safety & Governance (Scenario B: Guardrail-Blocked Payment)

**Visual**: Inspect high-risk payment `pay_100001` or run CLI script for Scenario B.  
**Speaker Notes**:
> *"Now let's examine payment `pay_100001`. The AI Decision Agent recommends sending a Payment Link. However, RecoverAI **never blindly trusts the AI**.*
> The Independent Guardrail Engine evaluates the transaction and triggers two rules: `MAX_RECOVERY_ATTEMPTS` (2 prior attempts already made) and `MAX_CUSTOMER_CONTACTS` (contact limit reached).*
> **Verdict**: `BLOCK`. **Zero calls** are made to Razorpay. The system fails safe and records a full audit log. This proves guardrails have absolute override authority over AI recommendations."*

---

### [4:20 – 5:00] Stage 6: Empirical Benchmark Evaluation & Conclusion

**Visual**: Show benchmark table from `docs/evaluation.md` / `data/evaluation_results.json`.  
**Speaker Notes**:
> *"Finally, we evaluated RecoverAI on a benchmark dataset of 2,500 failed payments (₹67.28 Lakh total value at risk, ₹40.36 Lakh ground-truth recoverable revenue).*
> At a 10% budget cutoff (Top 250 payments):
> - **RecoverAI** captures **₹13.49 Lakh** in revenue (**+11.31% lift over Amount-Only** and **+192.18% lift over Random**).
> - *Important Nuance*: While a Failure-Reason-Only rule captures high transaction counts, RecoverAI captures **significantly more total revenue**, proving that optimizing Expected Recovery Value achieves superior financial recovery."*

---

## Recommended Live Demo Commands

```bash
# 1. Run full 5-stage automated CLI pipeline (Scenarios A & B)
$env:PYTHONPATH="backend;."
python scripts/demo_pipeline.py pay_100003 pay_100001

# 2. Launch FastAPI Backend
uvicorn app.main:app --reload --port 8000

# 3. Launch React Merchant Frontend
cd frontend
npm run dev
```
