# RecoverAI — Architecture & Technical Specifications

## Overview
RecoverAI is an AI-powered revenue recovery system that optimizes payment recovery interventions for Razorpay merchants. It evaluates every failed payment in real-time to determine if intervention is worthwhile, calculates Expected Recovery Value ($EV$), recommends bounded recovery actions, verifies action safety using an independent deterministic Guardrail Engine, executes actions via Razorpay APIs, and logs full audit trails.

---

## System Architecture Diagram (Mermaid)

```mermaid
flowchart TD
    subgraph Frontend ["Merchant Portal"]
        UI["React / Vite Merchant Dashboard"]
    end

    subgraph Backend ["FastAPI Core Services"]
        API["FastAPI Ingestion & REST API Layer"]
        DB[(SQLAlchemy Database)]
        
        subgraph Pipeline ["Guardrail-Controlled Recovery Pipeline"]
            ScoringEngine["Recovery Scoring Engine\n(0-100 Score, P, EV=Amount×P)"]
            AIAgent["AI Decision Agent\n(Structured Action Recommendation)"]
            GuardrailEngine["INDEPENDENT GUARDRAIL ENGINE\n(Deterministic Safety Rules: ALLOW/MODIFY/BLOCK)"]
            ExecutionService["Recovery Execution Service\n(Workflow Enforcement & Audit Logging)"]
        end
    end

    subgraph External ["Razorpay Test Environment"]
        RazorpayAdapter["Razorpay Integration Adapter\n(Mock / Real Test Mode API)"]
        RazorpayAPI["Razorpay Payment Links API"]
        RazorpayWebhook["Razorpay Webhook Handler\n(HMAC-SHA256 Verification)"]
    end

    %% Flow Connections
    UI -->|Trigger Recovery / View Queue| API
    API --> ScoringEngine
    ScoringEngine --> AIAgent
    AIAgent -->|Proposed Decision| GuardrailEngine

    %% FORBIDDEN PATH
    AIAgent -.-X|DIRECT EXECUTION FORBIDDEN| RazorpayAdapter

    %% MANDATORY GATEWAY
    GuardrailEngine -->|ALLOW / MODIFY| ExecutionService
    GuardrailEngine -.->|BLOCK / HUMAN_REVIEW| DB

    ExecutionService --> RazorpayAdapter
    RazorpayAdapter -->|Create Payment Link| RazorpayAPI
    RazorpayAPI -->|payment.link.paid Event| RazorpayWebhook
    RazorpayWebhook -->|Verified State Update| DB
    ExecutionService -->|Immutable Audit Trail| DB
    DB --> UI
```

---

## Pipeline Component Breakdown

```
[Failed Payment]
       ↓
[Recovery Scoring Engine]  ──► Calculates 0-100 Score, Probability P, Expected Value (EV = Amount × P)
       ↓
[AI Decision Agent]       ──► Proposes action (RETRY, PAYMENT_LINK, WAIT, STOP, HUMAN_REVIEW)
       ↓
[Independent Guardrails]  ──► Mandatory Gatekeeper (Enforces 8 deterministic safety rules)
       ↓
[ALLOW / MODIFY]          ──► Proceeds to Execution Service
[BLOCK / HUMAN_REVIEW]    ──► Execution Safely Halted; Audit Record Saved
       ↓
[Razorpay Adapter]        ──► Calls Razorpay Test Mode Payment Link API
       ↓
[Razorpay Webhook]        ──► Signature Verified (HMAC-SHA256); Status -> RECOVERED
```

---

## Key Architectural Principles

1. **Strict Data Separation (Zero Data Leakage)**:
   Pre-decision feature inputs (`PaymentFeatureInputs`) strictly exclude ground-truth target labels (`recovered`, `amount_recovered`, `true_recovery_probability`). Pydantic `extra="forbid"` and runtime assertion `_check_data_leakage()` prevent leakage.

2. **Mandatory Guardrail Gatekeeper**:
   The AI Decision Agent **never has direct execution authority**. Every AI decision MUST pass through the Independent Guardrail Engine. If a guardrail evaluates to `BLOCK` or `HUMAN_REVIEW`, zero API calls are made to Razorpay.

3. **Abstracted Provider Pattern**:
   The `RazorpayProvider` interface decouples system logic from external API infrastructure. Supports `MockRazorpayProvider` for offline deterministic testing and `RealRazorpayAdapter` for live Razorpay Test Mode credentials.

4. **Idempotent Execution & Signature Security**:
   Recovery action execution enforces idempotency keys to prevent duplicate payment link creation. Incoming webhooks are authenticated via HMAC-SHA256 signature verification using `RAZORPAY_WEBHOOK_SECRET`.

5. **Immutable Audit Logging**:
   Every score calculation, AI decision, guardrail check, execution attempt, and webhook state transition is stored in an immutable `audit_logs` table for compliance and merchant auditability.
