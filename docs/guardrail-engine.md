# RecoverAI — Independent Guardrail Engine Specifications

> **Razorpay Buildathon 2026** | Deterministic Safety Layer & Policy Enforcement Engine

This document defines the architecture, rule hierarchy, configurable hard limits, operational state validation, high-value transaction escalation, velocity limits, audit logging, security boundaries, and AI override prevention for RecoverAI's **Independent Guardrail Engine**.

---

## 1. Core Principles & System Boundaries

The Independent Guardrail Engine enforces a single, unyielding operational mandate:
$$\text{"Does this proposed recovery intervention satisfy all deterministic merchant safety & risk policies?"}$$

While Phase 5's AI Decision Agent *recommends* an action, Phase 6's Guardrail Engine *evaluates and enforces policy*.

```
PROPOSED AI DECISION (Phase 5)
       │
       ▼
INDEPENDENT GUARDRAIL ENGINE (Phase 6 - 100% Deterministic Python)
├── Rule 1: Max Recovery Attempts (Limit: 2)
├── Rule 2: Max Customer Contacts (Limit: 2)
├── Rule 3: High-Value Escalation (Threshold: >= INR 25,000)
├── Rule 4: Operational State Eligibility (Block if RECOVERED / CANCELLED)
├── Rule 5: Velocity Protection (Cooldown: 60 mins)
├── Rule 6: Viability Thresholds (Min EV: INR 100)
└── Rule 7: Fail-Safe Fallback (Corrupt State Protection)
       │
       ▼
GUARDRAIL RESULT (ALLOW / MODIFY / BLOCK) ──► Audit Log (SQLite DB)
       │
       ▼
FUTURE EXECUTION LAYER (Phase 7+)
```

### AI Independence & Override Prevention
- **NO LLMs IN GUARDRAILS**: The Guardrail Engine is written in 100% pure Python code.
- **ZERO AI OVERRIDE**: The AI Decision Agent has **zero authority** to bypass or override a guardrail. Proposed decisions claiming `"guardrails_passed": true` are completely ignored and recalculated independently.

---

## 2. Configurable Hard Limits (`guardrails/config.py`)

All limits are centralized in `GuardrailConfig` without hardcoded magic numbers:

| Parameter | Configured Value | Operational Purpose |
| :--- | :---: | :--- |
| `MAX_RECOVERY_ATTEMPTS` | **2** | Maximum gateway retry attempts per payment |
| `MAX_CUSTOMER_CONTACTS` | **2** | Maximum direct messages (Payment Links) per customer |
| `HIGH_VALUE_THRESHOLD` | **INR 25,000.00** | Transactions $\ge \text{INR } 25,000$ modify action to `HUMAN_REVIEW` |
| `MIN_RECOVERY_PROBABILITY` | **0.15** | Blocks action if recovery probability $P < 15\%$ |
| `MIN_EXPECTED_RECOVERY_VALUE` | **INR 100.00** | Blocks action if Expected Recovery Value $< \text{INR } 100$ |
| `MAX_RECOMMENDED_DELAY_MINUTES` | **1440** (24h) | Caps maximum wait delay duration |
| `VELOCITY_WINDOW_MINUTES` | **60** mins | Enforces attempt cooldown between rapid actions |

---

## 3. Complete Guardrail Rule List

| Rule ID | Rule Name | Evaluated Status | Action on Violation |
| :--- | :--- | :---: | :--- |
| `MAX_RECOVERY_ATTEMPTS` | Maximum Recovery Attempts Limit | `BLOCK` | Blocks `RETRY` / `PAYMENT_LINK`; sets `final_action = STOP` |
| `MAX_CUSTOMER_CONTACTS` | Maximum Customer Contacts Limit | `BLOCK` | Blocks `PAYMENT_LINK` to prevent customer messaging spam |
| `HIGH_VALUE_REVIEW` | High-Value Human Escalation | `MODIFY` | Modifies action to `HUMAN_REVIEW` with `risk_level = HIGH` |
| `INVALID_PAYMENT_STATE` | Operational State Eligibility | `BLOCK` | Blocks action if payment status is `RECOVERED`, `CANCELLED`, `EXPIRED` |
| `VELOCITY_LIMIT` | Rapid Attempt Cooldown | `BLOCK` | Blocks `RETRY` if initiated $< 10$ mins after failure |
| `LOW_RECOVERY_POTENTIAL` | Minimum Viability Check | `BLOCK` | Blocks action if Expected Recovery Value $< \text{INR } 100$ |
| `UNREASONABLE_DELAY` | Max Wait Delay Validation | `MODIFY` | Caps recommended delay to $1,440$ minutes |
| `FAIL_SAFE_FALLBACK` | System Integrity Check | `BLOCK` | Blocks / routes to `HUMAN_REVIEW` on corrupt or missing state |

---

## 4. Fail-Safe Behavior & Audit Logging

### Fail-Safe Policy
If the Guardrail Engine encounters missing data, corrupt payment state, unknown actions, or system exceptions:
$$\text{State Uncertainty} \implies \text{BLOCK} \text{ or } \text{HUMAN\_REVIEW}$$
An uncertain payment is **never** permitted to automatically execute a financial action.

### Immutable Audit Trail (`AuditLog`)
Every guardrail evaluation persists an immutable audit entry to the database containing:
- `payment_id`
- `original_action`
- `final_action`
- `status` (`ALLOW`, `MODIFY`, `BLOCK`)
- `rules_triggered`
- `reason`
- `details` (risk level, human review flag, timestamp)
