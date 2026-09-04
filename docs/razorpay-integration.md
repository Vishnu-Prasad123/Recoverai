# RecoverAI — Razorpay Integration Adapter & Payment Link Workflows

> **Razorpay Buildathon 2026** | Integration Specifications & Webhook Security Model

This document defines the architecture, credential safety safeguards, provider abstraction, Payment Link workflow, HMAC-SHA256 webhook signature verification, idempotency strategy, error handling, security model, and API endpoints for RecoverAI's **Razorpay Integration Adapter**.

---

## 1. Razorpay Integration Architecture

The Razorpay integration is completely isolated from the AI Decision Agent, Recovery Scoring Engine, and Guardrail Engine behind an abstract Provider pattern.

```
EXECUTION PIPELINE FLOW:
Failed Payment ──► Scoring Engine ──► AI Decision Agent ──► Guardrail Engine
                                                                 │
                       ┌─────────────────────────────────────────┴────────────────────────────────────────┐
                       ▼                                                                                  ▼
            STATUS: BLOCK / MODIFY                                                                  STATUS: ALLOW
    ┌─────────────────────────────────────┐                                             ┌────────────────────────────────────┐
    │ Automatic API Execution PREVENTED   │                                             │ Recovery Execution Service         │
    │ Logged to AuditLog DB               │                                             │ (backend/app/services/...)        │
    └─────────────────────────────────────┘                                             └──────────────────┬─────────────────┘
                                                                                                           │
                                                                                        ┌──────────────────┴─────────────────┐
                                                                                        ▼                                    ▼
                                                                              MockRazorpayProvider                 RealRazorpayAdapter
                                                                              (Offline Test Mode)                  (Razorpay Sandbox REST API)
```

---

## 2. Test Mode & Credentials Configuration

Configure credentials via `.env` environment variables using Razorpay **Test Mode Sandbox**:

```env
RAZORPAY_MODE=mock                        # "mock" for zero-cost offline tests, "test" for Razorpay Sandbox
RAZORPAY_KEY_ID=rzp_test_your_key_id_here
RAZORPAY_KEY_SECRET=your_razorpay_key_secret_here
RAZORPAY_WEBHOOK_SECRET=your_razorpay_webhook_secret_here
```

### Credentials Safety Safeguards
- **NO SECRET LEAKAGE**: `RAZORPAY_KEY_SECRET` is never returned in API payloads, logs, audit details, or error tracebacks.
- **TEST MODE MANDATE**: Test Mode Key IDs must start with `rzp_test_`. Production keys are strictly rejected by `RazorpayConfig.validate_test_credentials()`.

---

## 3. Payment Link Workflow & Idempotency

### Workflow Execution Steps
1. Client issues request to `POST /api/recovery/execute` or `POST /api/recovery/payment-link`.
2. `RecoveryExecutionService` invokes `GuardrailService.evaluate_payment_guardrails()`.
3. If Guardrail status is `BLOCK` or `MODIFY` (`HUMAN_REVIEW`), automatic Razorpay call is **STRICTLY PREVENTED**.
4. If `ALLOW`, Idempotency check verifies if an active `RecoveryAttempt` already exists for this payment recovery attempt. If found, returns existing link (`IDEMPOTENT_SKIPPED`).
5. `RazorpayProvider` issues Payment Link API request (`POST https://api.razorpay.com/v1/payment_links`).
6. `RecoveryAttempt` and `AuditLog` records are persisted to SQLite database.

---

## 4. Webhook Signature Verification & State Synchronization

Razorpay webhooks (`POST /api/webhooks/razorpay`) enforce mandatory **HMAC-SHA256 signature verification**:

$$\text{HMAC-SHA256}(\text{raw\_body\_bytes}, \text{RAZORPAY\_WEBHOOK\_SECRET}) \equiv \text{X-Razorpay-Signature}$$

### Webhook Event Operational Transitions

| Razorpay Webhook Event | Operational Payment Status Transition | RecoveryAttempt Status |
| :--- | :--- | :--- |
| `payment.link.paid` | `FAILED` $\longrightarrow$ **`RECOVERED`** | `PENDING` $\rightarrow$ **`SUCCESS`** |
| `payment.link.expired` | `FAILED` $\longrightarrow$ **`EXPIRED`** | `PENDING` $\rightarrow$ **`EXPIRED`** |
| `payment.failed` | `FAILED` (Unchanged) | `PENDING` $\rightarrow$ **`FAILED`** |

---

## 5. REST API Endpoints

- **`POST /api/recovery/execute`**: Executes recovery action for a payment (requires Guardrail `ALLOW`).
- **`POST /api/recovery/payment-link`**: Creates Razorpay Payment Link for a payment (requires Guardrail `ALLOW`).
- **`GET /api/recovery/{payment_id}`**: Retrieves recovery attempt history and link details.
- **`POST /api/webhooks/razorpay`**: Razorpay webhook handler with HMAC signature verification.

---

## 6. Razorpay API Limitations

1. **Card/UPI Gateway Retries**: Standard Razorpay Payment Links API allows customers to complete payment via UPI, Credit/Debit Cards, Netbanking, or Wallets. Direct gateway auto-debit retries without customer interaction are restricted by Indian card-on-file tokenization rules (e.g. RBI e-mandates). RecoverAI surfaces standard Payment Links as the primary multi-channel recovery method.
