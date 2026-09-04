# RecoverAI — Guardrail-Controlled AI Revenue Recovery Agent for Razorpay

> **Razorpay Buildathon 2026 Submission** | Track: AI for Digital Commerce & Payments

"RecoverAI is an AI-powered revenue recovery agent for failed payments. It ranks revenue at risk using Expected Recovery Value, recommends bounded recovery actions, enforces independent safety guardrails, executes approved workflows through Razorpay Test Mode, verifies outcomes through webhooks, and maintains an auditable recovery trail."

---

## 🚀 Key Architectural Highlights

1. **Intelligent Payment Prioritization**: Calculates Expected Recovery Value ($EV = \text{Amount} \times \text{Probability}$) to maximize merchant cash flow recovery within fixed intervention budgets.
2. **Structured AI Decision Agent**: Produces strictly validated Pydantic JSON schema actions (`RETRY`, `PAYMENT_LINK`, `WAIT`, `STOP`, `HUMAN_REVIEW`).
3. **Independent Guardrail Engine**: Mandatory gatekeeper enforcing 8 deterministic safety rules (`MAX_RECOVERY_ATTEMPTS`, `MAX_CUSTOMER_CONTACTS`, `HIGH_VALUE_REVIEW`, etc.). If guardrails block an action, **zero calls** are made to Razorpay.
4. **Razorpay Integration Adapter**: Seamlessly creates official Razorpay Payment Links (Test Mode) and verifies incoming webhooks via HMAC-SHA256 signature checking.
5. **Empirically Proven Impact**: Rigorous evaluation on 2,500 failed payment records demonstrating **+11.31% revenue lift over Amount-Only** and **+192.18% revenue lift over Random** baselines.
6. **Polished Merchant Dashboard & Auditability**: Real-time React dashboard with executive KPI cards, operational recovery queue, 5-stage payment lifecycle modal, and immutable audit logs.

---

## 📐 Pipeline Architecture

```
[Failed Payment]
       ↓
[Recovery Scoring Engine]  ──► Calculates 0-100 Score, Probability P, Expected Value (EV = Amount × P)
       ↓
[AI Decision Agent]       ──► Proposes action (RETRY, PAYMENT_LINK, WAIT, STOP, HUMAN_REVIEW)
       ↓
[Independent Guardrails]  ──► Mandatory Gatekeeper (Enforces 8 deterministic safety rules)
       ↓
[ALLOW / MODIFY]          ──► Execution Layer calls Razorpay API
[BLOCK / HUMAN_REVIEW]    ──► Execution Safely Halted (0 Provider Calls); Audit Logged
       ↓
[Razorpay Webhook]        ──► HMAC-SHA256 Signature Verified; DB Status -> RECOVERED
```

*Note: The AI Agent NEVER has direct execution authority to call external payment APIs without passing through the Independent Guardrail Engine.*

---

## 🛠️ Quickstart & Local Setup

### Prerequisites
- **Python**: 3.10+ (Virtual environment recommended)
- **Node.js**: v18+ (npm / npx)

---

### Step 1: Backend Setup (FastAPI)

1. Open PowerShell / Terminal in project root:
   ```powershell
   $env:PYTHONPATH="backend;."
   .\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
   ```
2. Verify API Health:
   - URL: `http://localhost:8000/api/health`
   - Response: `{"status": "healthy", "database": {"connected": true}}`

---

### Step 2: Merchant Dashboard Setup (React + Vite)

1. Open a new terminal in `frontend/`:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Open Dashboard in Browser:
   - Access `http://localhost:5173`

---

### Step 3: Run Live End-to-End CLI Pipeline Demo

Run the automated CLI script demonstrating both **Scenario A (Approved Recovery)** and **Scenario B (Guardrail Blocked)**:

```powershell
$env:PYTHONPATH="backend;."
.\backend\venv\Scripts\python.exe scripts/demo_pipeline.py pay_100003 pay_100001
```

---

### Step 4: Run Complete Test Suite & Benchmark Evaluation

Run the 79 automated Pytest tests and offline model evaluation harness:

```powershell
# Run Unit & End-to-End Test Suite (79 passing tests)
$env:PYTHONPATH="backend;."
.\backend\venv\Scripts\python.exe -m pytest tests/ -v

# Run Offline Evaluation Harness
.\backend\venv\Scripts\python.exe ai/evaluate_scoring.py
```

---

## ⚙️ Environment Variables (`.env`)

Copy `.env.example` to `.env` in the root directory:

```env
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=sqlite:///./recoverai.db

# Razorpay Test Credentials
RAZORPAY_KEY_ID=rzp_test_mock_12345
RAZORPAY_KEY_SECRET=mock_secret_key_12345
RAZORPAY_WEBHOOK_SECRET=whsec_mock_secret_key_12345

# AI Provider Configuration
LLM_PROVIDER=mock
MOCK_LLM_RESPONSE_TIME_MS=20
```

---

## 📈 Benchmark Evaluation Summary (Verified Phase 10)

> [!IMPORTANT]
> **Data Leakage & Evaluation Disclaimer**:
> Evaluation is performed offline on a synthetic dataset of **2,500 payments** across **800 unique customers** generated with fixed seed `42`. Features passed to model inference (`PaymentFeatureInputs`) strictly exclude ground-truth labels (`recovered`, `amount_recovered`, `true_recovery_probability`).

### Baseline Comparison at Budget Cutoffs

| Intervention Budget | Strategy | Selected Payments | Recovered Revenue (INR) | % GT Revenue Captured | Lift vs Amount-Only | Lift vs Random |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Top 10% Cutoff** (250) | **RecoverAI** | 250 | **₹13,49,320.63** | **33.43%** | **+11.31%** | **+192.18%** |
| | Amount-Only | 250 | ₹12,12,202.54 | 30.04% | — | +162.49% |
| | Random (Seed 42) | 250 | ₹4,61,816.16 | 11.44% | -61.90% | — |
| **Top 20% Cutoff** (500) | **RecoverAI** | 500 | **₹20,68,032.64** | **51.24%** | **+6.34%** | **+135.62%** |
| | Amount-Only | 500 | ₹19,44,775.25 | 48.19% | — | +121.58% |
| | Random (Seed 42) | 500 | ₹8,77,688.33 | 21.75% | -54.87% | — |
| **Top 30% Cutoff** (750) | **RecoverAI** | 750 | **₹25,46,909.55** | **63.11%** | **+4.61%** | **+91.93%** |
| | Amount-Only | 750 | ₹24,34,606.82 | 60.33% | — | +83.47% |
| | Random (Seed 42) | 750 | ₹13,27,013.69 | 32.88% | -45.49% | — |

*Nuance Note: Failure-Reason-Only rule captures high transaction counts, but RecoverAI captures significantly more total revenue, demonstrating revenue optimization over simple transaction count maximization.*

---

## 📂 Key Project Documentation

- [Architecture & Specifications](file:///c:/Users/hp/OneDrive/Desktop/rai/recoverai/docs/architecture.md)
- [Data Model & Database Schema](file:///c:/Users/hp/OneDrive/Desktop/rai/recoverai/docs/data-model.md)
- [Dataset Specifications & Leakage Prevention](file:///c:/Users/hp/OneDrive/Desktop/rai/recoverai/docs/dataset.md)
- [Razorpay Integration & Webhook Adapter](file:///c:/Users/hp/OneDrive/Desktop/rai/recoverai/docs/razorpay-integration.md)
- [Evaluation & Baseline Report](file:///c:/Users/hp/OneDrive/Desktop/rai/recoverai/docs/evaluation.md)
- [5-Minute Buildathon Demo Script](file:///c:/Users/hp/OneDrive/Desktop/rai/recoverai/docs/demo-script.md)

---

## 🔒 Security & Compliance

- **Zero Hardcoded Secrets**: Credentials managed via Pydantic environment settings.
- **Git Safety**: `.env` and SQLite database files (`.db`) ignored by `.gitignore`.
- **HMAC Signature Check**: Webhooks validated using SHA-256 digests.
- **Audit Logging**: Immutable event log tracking every scoring, decision, guardrail check, and provider API call.
