# RecoverAI — AI Decision Agent Specifications

> **Razorpay Buildathon 2026** | AI Decision Architecture & Action Recommendation Layer

This document defines the architecture, prompt design, allowed actions, provider abstraction, structured Pydantic output, validation fallbacks, security boundaries, and guardrail separation for RecoverAI's **AI Decision Agent**.

---

## 1. Core Principles & System Boundaries

The AI Decision Agent answers a fundamental operational question:
$$\text{"What action should we recommend for this failed payment?"}$$

While Phase 4's Recovery Scoring Engine produces quantitative estimates (Score, Probability, EV, Priority), the AI Decision Agent evaluates payment context and merchant economics to recommend the optimal intervention.

### Architectural Separation
```
PAYMENT FEATURES (Pre-Decision Only)
       │
       ▼
PHASE 4: RECOVERY SCORING ENGINE  ──► Score, Prob, EV, Priority, Factors
       │
       ▼
PHASE 5: AI DECISION AGENT       ──► Proposed RecoveryDecision Recommendation
       │
       ▼
PHASE 6: GUARDRAIL ENGINE        ──► ALLOW / MODIFY / BLOCK Policy Check
       │
       ▼
EXECUTION LAYER                  ──► Gateway Retry / Payment Link / Contact
```

---

## 2. Allowed Actions (Strict Enum)

The agent is strictly constrained to output **EXACTLY ONE** of five predefined actions:

| Action | Operational Semantics | Example Scenario |
| :--- | :--- | :--- |
| **`RETRY`** | Direct gateway re-attempt via Razorpay gateway | Transient bank timeout or network glitch with 0 prior recovery attempts |
| **`PAYMENT_LINK`** | Issue alternate payment link via WhatsApp / Email / SMS | Insufficient funds, card authorization decline, or UPI failure |
| **`WAIT`** | Delay action by recommended delay minutes | Recent gateway network degradation spike |
| **`STOP`** | Cease all further recovery attempts | Account blocked, or maximum recovery attempt limit reached |
| **`HUMAN_REVIEW`** | Escalate to merchant operations team | Ambiguous failure, high transaction risk, or model output parsing fallback |

> **SECURITY ISOLATION**: The AI Decision Agent recommends proposed actions only. It possesses **zero** financial tools, **zero** execution capabilities, and **zero** access to post-action outcome labels.

---

## 3. Provider Abstraction & Test Mode

To ensure zero-cost, 100% offline, reproducible automated testing, the agent uses an abstract provider pattern:

```
LLMProvider (Abstract Interface)
├── MockLLMProvider (Deterministic, 100% offline, rule-aware provider for tests)
└── RealLLMProvider (Production LLM provider accessing Gemini or OpenAI API)
```

- Environment credentials (`LLM_API_KEY`, `LLM_MODEL`) are parsed safely from environment variables without hardcoded keys.
- If credentials are missing or API limits fail, the agent triggers a safe fallback.

---

## 4. Structured Output Pydantic Schema

Output validation is enforced using the `RecoveryDecision` Pydantic model:

```json
{
  "payment_id": "pay_100001",
  "action": "PAYMENT_LINK",
  "confidence": 0.85,
  "rationale": "Failure reason 'insufficient_funds' suggests an alternate payment path; sending a Payment Link to customer with 75% payment history.",
  "expected_recovery_value": 4349.14,
  "priority": "HIGH",
  "recommended_delay_minutes": 0,
  "risk_level": "LOW",
  "guardrail_notes": "Proposed recommendation pending Guardrail Engine check."
}
```

---

## 5. Fallback Safety Handling

If an LLM API output fails Pydantic schema validation or returns unparseable text:
1. The agent intercepts the exception.
2. It automatically generates a safe fallback `RecoveryDecision`:
   - `action`: **`HUMAN_REVIEW`**
   - `confidence`: `0.0`
   - `risk_level`: `"HIGH"`
   - `rationale`: `"Decision Engine Fallback: Schema validation failed. Routed for merchant human review."`

---

## 6. Zero Data Leakage Proof

Input feature dictionaries are checked at runtime before invoking LLM providers:
```python
forbidden_fields = {"recovered", "amount_recovered", "true_recovery_probability"}
if set(features_dict.keys()).intersection(forbidden_fields):
    raise ValueError("DATA LEAKAGE DETECTED!")
```
Ground-truth target labels are strictly excluded from all agent prompt contexts.
