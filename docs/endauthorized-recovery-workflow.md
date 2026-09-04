# RecoverAI — End-to-End Recovery Action Execution & Workflow Specifications

> **Razorpay Buildathon 2026** | Comprehensive Pipeline, Guardrail Enforcement & Execution Architecture

This document defines the complete end-to-end recovery pipeline, operational state machine, safety gate enforcement, Razorpay adapter integration, HMAC-SHA256 webhook state synchronization, secret protection, and step-by-step local demonstration procedures for RecoverAI.

---

## 1. End-to-End Pipeline Architecture

RecoverAI unifies 5 independent engineering layers into a single, deterministic recovery workflow:

```
[1. FAILED PAYMENT]
       │
       ▼
[2. RECOVERY SCORING ENGINE] ──► Score (0-100), Probability (0-1), Expected Recovery Value (EV)
       │
       ▼
[3. AI DECISION AGENT]       ──► Recommends Action (RETRY, PAYMENT_LINK, WAIT, STOP, HUMAN_REVIEW) + Rationale
       │
       ▼
[4. INDEPENDENT GUARDRAIL ENGINE] (100% Deterministic Safety Layer)
       ├── Evaluates 8 Business Rules (Max Retries, Contacts, High-Value, Cooldown, Operational State)
       └── Computes Status: ALLOW, MODIFY, or BLOCK
       │
       ├──► STATUS = BLOCK / MODIFY (HUMAN_REVIEW)
       │    └── AUTOMATIC API CALL STRICTLY PREVENTED. Audit Log Recorded. Stop.
       │
       └──► STATUS = ALLOW
            │
            ▼
[5. EXECUTION LAYER & WEBHOOK SYNC]
       ├── Idempotency Check (Prevents Duplicate Links)
       ├── Razorpay Integration Adapter (Issues Test Mode Payment Link)
       ├── DB Persistence (RecoveryAttempt & AuditLog Records)
       └── Webhook Verification (HMAC-SHA256 Signature -> Updates DB Status to RECOVERED)
```

---

## 2. Recovery Operational State Machine

```
FAILED ──► [Pipeline Execution] ──┬──► STOPPED_BY_GUARDRAIL (Status: BLOCK)
                                  ├──► ESCALATED_HUMAN_REVIEW (Status: MODIFY)
                                  └──► RECOVERY_INITIATED / PENDING (Status: ALLOW)
                                              │
                                              ▼ [Razorpay Webhook Event]
                                  ┌───────────┴───────────┐
                                  ▼                       ▼
                              RECOVERED                EXPIRED / FAILED
```

- **Operational Outcome Tracking**: Recovered revenue is calculated strictly from live operational state updates (`RECOVERED`), never from ground-truth dataset labels.

---

## 3. Guardrail Safety Gate & AI Independence

- **Zero AI Override**: The AI Decision Agent has **zero authority** to execute financial transactions or override guardrail rules.
- **Safety Gate Rule**: The execution service (`RecoveryExecutionService.execute_full_recovery_pipeline()`) verifies `g_result.status == ALLOW`. If the guardrail returns `BLOCK` or `MODIFY` (`HUMAN_REVIEW`), external API calls are **STRICTLY PREVENTED**.

---

## 4. REST API Endpoint Reference

### 1. `POST /api/recovery/execute?payment_id={payment_id}`
Executes the unified 5-step end-to-end recovery pipeline for a payment.

### 2. `GET /api/recovery/{payment_id}`
Retrieves comprehensive payment details, scoring metrics, AI recommendation, guardrail decision, execution status, Payment Link details, attempt history, and audit logs.

### 3. `POST /api/webhooks/razorpay`
Processes incoming Razorpay webhooks (`payment.link.paid`, `payment.link.expired`) using HMAC-SHA256 signature verification.

---

## 5. Step-by-Step Local Demonstration Guide

To execute the live end-to-end recovery demonstration script for the Razorpay Buildathon:

```powershell
# Run full end-to-end recovery pipeline demonstration for payment pay_100003
$env:PYTHONPATH="backend"; .\backend\venv\Scripts\python.exe scripts/demo_pipeline.py pay_100003
```

### Expected Output Summary:
1. Target payment details (`pay_100003`, amount: INR 4,500.00).
2. Stage 1 Scoring Metrics: Score, Recovery Probability, Expected Value.
3. Stage 2 AI Recommendation: Recommended action & rationale.
4. Stage 3 Guardrail Engine: Evaluation of 8 safety rules (`ALLOW`).
5. Stage 4 Razorpay Execution: Payment Link creation (`plink_...`, `short_url`).
6. Stage 5 Webhook Sync: HMAC signature verification & DB state transition to `RECOVERED`.
