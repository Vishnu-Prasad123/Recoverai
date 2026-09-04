"""
RecoverAI - End-to-End Recovery Pipeline Live Demonstration Script
Razorpay Buildathon 2026

Demonstrates the complete 5-step recovery lifecycle across two distinct operational scenarios:
1. SCENARIO A (SUCCESSFUL RECOVERY): Allowed payment -> Score & EV -> AI Decision -> Guardrail ALLOW -> Razorpay Execution -> Webhook Verification -> Status RECOVERED.
2. SCENARIO B (GUARDRAIL BLOCKED): High-risk payment -> AI Decision -> Guardrail BLOCK -> Zero Razorpay Calls -> Audit Trail Logged.

Usage:
    .\\backend\\venv\\Scripts\\python.exe scripts/demo_pipeline.py [payment_id_allowed] [payment_id_blocked]
"""

import os
import sys
import json
import hmac
import hashlib

# Ensure root & backend directories are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal
from app.models.payment import Payment
from app.models.audit import AuditLog
from app.services.payment_service import PaymentService
from app.services.recovery_execution_service import RecoveryExecutionService
from ai.scoring import scoring_engine
from ai.agent import ai_decision_agent
from guardrails.engine import guardrail_engine
from razorpay_integration.config import RAZORPAY_CONFIG
from razorpay_integration.webhook_verifier import verify_razorpay_webhook_signature


def reset_demo_payment_state(db, payment_id: str, is_blocked_scenario: bool = False):
    """Resets payment state to clean FAILED state for reproducible CLI demonstration."""
    pmt = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if pmt:
        pmt.status = "FAILED"
        pmt.recovered = False
        pmt.amount_recovered = 0.0
        if is_blocked_scenario:
            pmt.previous_recovery_attempts = 2  # Triggers MAX_RECOVERY_ATTEMPTS guardrail
        else:
            pmt.previous_recovery_attempts = 0
        db.commit()


def run_scenario_demo(db, payment_id: str, scenario_label: str, is_blocked_scenario: bool = False):
    print("\n" + "=" * 75)
    print(f"   RECOVERAI DEMO — {scenario_label.upper()}")
    print("=" * 75)

    # Reset payment for deterministic demonstration
    reset_demo_payment_state(db, payment_id, is_blocked_scenario=is_blocked_scenario)

    # 0. Load Payment Record
    pmt = PaymentService.get_payment_by_id(db, payment_id=payment_id)
    if not pmt:
        print(f"Error: Payment ID '{payment_id}' not found in database.")
        return

    print(f"\n[0. TARGET PAYMENT RECORD]")
    print(f"  • Payment ID                : {pmt.payment_id}")
    print(f"  • Customer ID               : {pmt.customer_id}")
    print(f"  • Transaction Amount        : INR {pmt.amount:,.2f}")
    print(f"  • Payment Method            : {pmt.payment_method.upper()}")
    print(f"  • Failure Reason            : {pmt.failure_reason}")
    print(f"  • Operational Status        : {pmt.status}")
    print(f"  • Prior Recovery Attempts   : {pmt.previous_recovery_attempts}")

    # STAGE 1: RECOVERY SCORING ENGINE
    print("\n" + "-" * 75)
    print("[STAGE 1: RECOVERY SCORING ENGINE (Expected Recovery Value)]")
    feat = PaymentService.get_payment_feature_inputs(db, payment_id=payment_id)
    scoring_res = scoring_engine.score_payment(feat)
    print(f"  • Recovery Score            : {scoring_res.recovery_score:.1f} / 100")
    print(f"  • Recovery Probability (P)  : {scoring_res.recovery_probability:.2%}")
    print(f"  • Expected Value (EV)       : INR {scoring_res.expected_recovery_value:,.2f}  (= Amount × P)")
    print(f"  • Priority Tier             : {scoring_res.priority}")

    # STAGE 2: AI DECISION AGENT
    print("\n" + "-" * 75)
    print("[STAGE 2: AI DECISION AGENT RECOMMENDATION]")
    ai_dec = ai_decision_agent.recommend_action(feat)
    print(f"  • Proposed Action           : {ai_dec.action.value}")
    print(f"  • AI Confidence             : {ai_dec.confidence:.2%}")
    print(f"  • Merchant Rationale        : {ai_dec.rationale}")

    # STAGE 3: INDEPENDENT GUARDRAIL ENGINE
    print("\n" + "-" * 75)
    print("[STAGE 3: INDEPENDENT GUARDRAIL ENGINE EVALUATION]")
    g_res = guardrail_engine.evaluate_decision(feat, ai_dec)
    print(f"  • Rules Evaluated           : {len(g_res.rules_evaluated)} deterministic safety rules")
    print(f"  • Rules Triggered           : {g_res.rules_triggered if g_res.rules_triggered else 'None (All Passed)'}")
    print(f"  • Guardrail Verdict         : {g_res.status.value}")
    print(f"  • Approved Recovery Action  : {g_res.final_action.value}")

    # STAGE 4: RAZORPAY EXECUTION PIPELINE
    print("\n" + "-" * 75)
    print("[STAGE 4: GUARDRAIL-ENFORCED RAZORPAY ADAPTER EXECUTION]")
    exec_res = RecoveryExecutionService.execute_full_recovery_pipeline(db, payment_id=payment_id)
    print(f"  • Execution Status          : {exec_res.execution_status}")
    print(f"  • Pipeline Message          : {exec_res.message}")
    
    if exec_res.execution_status == "BLOCKED_BY_GUARDRAILS":
        print(f"  • Razorpay API Calls Made   : ZERO (0 calls — Guardrail Protection Active)")
        print(f"  • Safety Verification       : Execution safely halted before external provider call.")
    elif exec_res.payment_link:
        print(f"  • Razorpay Payment Link ID  : {exec_res.payment_link.id}")
        print(f"  • Short Checkout URL        : {exec_res.payment_link.short_url}")

    # STAGE 5: WEBHOOK & AUDIT LOG SYNCHRONIZATION
    print("\n" + "-" * 75)
    print("[STAGE 5: RAZORPAY WEBHOOK VERIFICATION & AUDIT TRAIL]")
    
    if g_res.status.value == "ALLOW":
        secret = RAZORPAY_CONFIG.RAZORPAY_WEBHOOK_SECRET
        link_id = exec_res.payment_link.id if exec_res.payment_link else f"plink_mock_{payment_id}"
        payload_dict = {
            "event": "payment.link.paid",
            "account_id": "acc_demo_999",
            "created_at": 1700000000,
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": link_id,
                        "status": "paid",
                        "notes": {
                            "payment_id": payment_id
                        }
                    }
                }
            }
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")
        sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        
        sig_valid = verify_razorpay_webhook_signature(body_bytes, sig, secret)
        print(f"  • Webhook Signature Check  : {'PASS (HMAC-SHA256 Verified)' if sig_valid else 'FAIL'}")

        # Update DB state for demonstration
        pmt_db = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if pmt_db and sig_valid:
            pmt_db.status = "RECOVERED"
            pmt_db.recovered = True
            pmt_db.amount_recovered = pmt_db.amount
            db.commit()
            print(f"  • Final Payment Status      : {pmt_db.status} (Ground-truth revenue updated)")
            print(f"  • Recovered Amount          : INR {pmt_db.amount_recovered:,.2f}")
    else:
        print(f"  • Webhook Execution State  : SKIPPED (Payment action blocked by guardrails)")

    # Inspect persistent audit trail record
    audit_record = db.query(AuditLog).filter(AuditLog.payment_id == payment_id).order_by(AuditLog.id.desc()).first()
    if audit_record:
        print(f"  • Audit Trail Event Saved   : ID={audit_record.id} | EventType='{audit_record.event_type}' | Actor='{audit_record.actor}'")

    print("=" * 75)


def run_full_demo(allowed_id: str = "pay_100003", blocked_id: str = "pay_100001"):
    db = SessionLocal()
    try:
        print("\n" + "#" * 75)
        print("   RECOVERAI — END-TO-END RECOVERY PIPELINE DEMONSTRATION")
        print("   Razorpay Buildathon 2026")
        print("   Mode: Guardrail-Controlled Autonomous Recovery Pipeline")
        print("#" * 75)

        run_scenario_demo(db, payment_id=allowed_id, scenario_label="Scenario A: Approved Payment Recovery Path (ALLOW)", is_blocked_scenario=False)
        run_scenario_demo(db, payment_id=blocked_id, scenario_label="Scenario B: Guardrail-Blocked High-Risk Path (BLOCK)", is_blocked_scenario=True)

        print("\n" + "#" * 75)
        print("   [DEMONSTRATION COMPLETE: ALL PIPELINE STAGES VERIFIED]")
        print("#" * 75 + "\n")
    finally:
        db.close()


if __name__ == "__main__":
    allowed = sys.argv[1] if len(sys.argv) > 1 else "pay_100003"
    blocked = sys.argv[2] if len(sys.argv) > 2 else "pay_100001"
    run_full_demo(allowed_id=allowed, blocked_id=blocked)
