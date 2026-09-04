import React, { useState } from 'react';
import { PaymentFullDetail } from '../types';
import { executeRecovery } from '../services/api';
import { X, CheckCircle2, Shield, Cpu, Activity, ExternalLink, RefreshCw, AlertCircle, AlertTriangle } from 'lucide-react';

interface PaymentDetailModalProps {
  detail: PaymentFullDetail | null;
  loading: boolean;
  onClose: () => void;
  onRefresh: (paymentId: string) => void;
}

export const PaymentDetailModal: React.FC<PaymentDetailModalProps> = ({ detail, loading, onClose, onRefresh }) => {
  const [executing, setExecuting] = useState(false);
  const [execMessage, setExecMessage] = useState<string | null>(null);

  if (!detail && loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
        <div className="bg-[#131A29] border border-[#1E293B] p-8 rounded-2xl flex flex-col items-center space-y-4">
          <RefreshCw className="h-8 w-8 text-blue-400 animate-spin" />
          <p className="text-slate-300 text-sm font-medium">Fetching 5-Stage Recovery Pipeline Details...</p>
        </div>
      </div>
    );
  }

  if (!detail) return null;

  const handleRunRecovery = async () => {
    setExecuting(true);
    setExecMessage(null);
    try {
      const res = await executeRecovery(detail.payment_id);
      setExecMessage(`[${res.execution_status}] ${res.message}`);
      onRefresh(detail.payment_id);
    } catch (err: any) {
      setExecMessage(`Execution Error: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const gStatus = detail.guardrail_evaluation?.status || 'ALLOW';
  const isBlock = gStatus === 'BLOCK';
  const isModify = gStatus === 'MODIFY';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 overflow-y-auto">
      <div className="bg-[#131A29] border border-[#1E293B] rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col my-8">
        
        {/* Modal Header */}
        <div className="sticky top-0 bg-[#131A29]/95 backdrop-blur border-b border-[#1E293B] px-6 py-4 flex items-center justify-between z-20">
          <div>
            <div className="flex items-center space-x-3">
              <h3 className="text-xl font-bold text-white font-mono">{detail.payment_id}</h3>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                detail.operational_status === 'RECOVERED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                detail.operational_status === 'RECOVERY_INITIATED' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}>
                {detail.operational_status}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">Customer: <span className="text-slate-200 font-mono">{detail.customer_id}</span> | Amount: <strong className="text-white">₹{detail.amount.toLocaleString('en-IN')}</strong></p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleRunRecovery}
              disabled={executing || isBlock}
              className={`px-4 py-2 rounded-xl font-semibold text-xs transition-all flex items-center space-x-2 shadow-lg ${
                isBlock
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30 cursor-not-allowed'
                  : isModify
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30'
                  : 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-500 hover:to-cyan-500 shadow-blue-500/20'
              }`}
            >
              {executing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
              <span>{isBlock ? 'Blocked by Guardrails' : isModify ? 'Review Required' : 'Execute Recovery Pipeline'}</span>
            </button>

            <button onClick={onClose} className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/60 transition">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {execMessage && (
          <div className="bg-blue-900/30 border-b border-blue-500/30 px-6 py-2.5 text-xs font-mono text-cyan-300 flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-cyan-400 flex-shrink-0" />
            <span>{execMessage}</span>
          </div>
        )}

        {/* 5-Stage Recovery Timeline Body */}
        <div className="p-6 space-y-6">

          {/* STAGE 1: FAILED PAYMENT RECORD */}
          <div className="p-4 rounded-xl bg-[#0B0F17] border border-[#1E293B] relative overflow-hidden">
            <div className="flex items-center space-x-2 text-slate-400 font-semibold text-xs uppercase tracking-wider mb-2">
              <span className="h-5 w-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center text-[10px] font-bold">1</span>
              <span>Failed Payment Context</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div><span className="text-slate-400">Failure Reason:</span> <p className="font-semibold text-rose-400 capitalize">{detail.failure_reason.replace(/_/g, ' ')}</p></div>
              <div><span className="text-slate-400">Payment Method:</span> <p className="font-semibold text-white uppercase">{detail.payment_method}</p></div>
              <div><span className="text-slate-400">Prior Retries:</span> <p className="font-semibold text-white">{detail.previous_recovery_attempts} attempts</p></div>
              <div><span className="text-slate-400">Currency:</span> <p className="font-semibold text-white">{detail.currency}</p></div>
            </div>
          </div>

          {/* STAGE 2: RECOVERY SCORING ENGINE */}
          <div className="p-4 rounded-xl bg-[#0B0F17] border border-amber-500/30 relative">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2 text-amber-400 font-semibold text-xs uppercase tracking-wider">
                <span className="h-5 w-5 rounded-full bg-amber-500/20 text-amber-300 flex items-center justify-center text-[10px] font-bold">2</span>
                <span>Recovery Scoring Engine Output</span>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                detail.scoring.priority === 'HIGH' ? 'bg-emerald-500/20 text-emerald-400' :
                detail.scoring.priority === 'MEDIUM' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-700 text-slate-300'
              }`}>
                {detail.scoring.priority} PRIORITY
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs bg-[#131A29] p-3 rounded-lg border border-[#1E293B]">
              <div>
                <span className="text-slate-400">Recovery Score:</span>
                <p className="text-lg font-bold text-amber-400">{detail.scoring.recovery_score.toFixed(1)} / 100</p>
              </div>
              <div>
                <span className="text-slate-400">Recovery Probability (P):</span>
                <p className="text-lg font-bold text-cyan-400">{(detail.scoring.recovery_probability * 100).toFixed(1)}%</p>
              </div>
              <div>
                <span className="text-slate-400">Expected Recovery Value (EV):</span>
                <p className="text-lg font-bold text-emerald-400">₹{detail.scoring.expected_recovery_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</p>
              </div>
            </div>
          </div>

          {/* STAGE 3: AI DECISION AGENT */}
          <div className="p-4 rounded-xl bg-[#0B0F17] border border-blue-500/30 relative">
            <div className="flex items-center space-x-2 text-blue-400 font-semibold text-xs uppercase tracking-wider mb-2">
              <Cpu className="h-4 w-4" />
              <span className="h-5 w-5 rounded-full bg-blue-500/20 text-blue-300 flex items-center justify-center text-[10px] font-bold">3</span>
              <span>AI Decision Agent Recommendation</span>
            </div>
            {detail.ai_recommendation ? (
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Recommended Action:</span>
                  <span className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 font-mono font-bold text-xs">{detail.ai_recommendation.action}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Agent Confidence:</span>
                  <span className="font-semibold text-slate-200">{(detail.ai_recommendation.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="p-2.5 rounded bg-[#131A29] border border-[#1E293B] text-slate-300 leading-relaxed italic">
                  "{detail.ai_recommendation.rationale}"
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">AI recommendation pending execution.</p>
            )}
          </div>

          {/* STAGE 4: INDEPENDENT GUARDRAIL ENGINE */}
          <div className={`p-4 rounded-xl bg-[#0B0F17] border relative ${
            isBlock ? 'border-rose-500/40' : isModify ? 'border-amber-500/40' : 'border-emerald-500/40'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2 text-slate-200 font-semibold text-xs uppercase tracking-wider">
                <Shield className="h-4 w-4 text-emerald-400" />
                <span className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-300 flex items-center justify-center text-[10px] font-bold">4</span>
                <span>Independent Guardrail Safety Evaluation</span>
              </div>
              <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                isBlock ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                isModify ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              }`}>
                STATUS: {gStatus}
              </span>
            </div>

            {detail.guardrail_evaluation ? (
              <div className="space-y-2 text-xs">
                <p className="text-slate-300 font-mono text-[11px] bg-[#131A29] p-2.5 rounded border border-[#1E293B]">
                  {detail.guardrail_evaluation.reason}
                </p>
                {detail.guardrail_evaluation.rules_triggered.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-4 w-4 text-rose-400" />
                    <span className="text-rose-300 text-[11px]">Triggered Rules: <strong>{detail.guardrail_evaluation.rules_triggered.join(', ')}</strong></span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-400">All 8 deterministic safety rules evaluated independently.</p>
            )}
          </div>

          {/* STAGE 5: RAZORPAY EXECUTION & WEBHOOK AUDIT */}
          <div className="p-4 rounded-xl bg-[#0B0F17] border border-cyan-500/30 relative space-y-3">
            <div className="flex items-center space-x-2 text-cyan-400 font-semibold text-xs uppercase tracking-wider">
              <CheckCircle2 className="h-4 w-4" />
              <span className="h-5 w-5 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-[10px] font-bold">5</span>
              <span>Razorpay Provider Execution & Webhook Audit</span>
            </div>

            {detail.attempts && detail.attempts.length > 0 ? (
              <div className="space-y-2 text-xs">
                {detail.attempts.map((att, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-[#131A29] border border-[#1E293B] flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-cyan-300 font-bold">{att.attempt_id}</span>
                        <span className="text-slate-400 text-[11px]">Action: {att.action}</span>
                      </div>
                      {att.response_payload?.short_url && (
                        <a
                          href={att.response_payload.short_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-400 hover:underline text-[11px] flex items-center space-x-1 mt-1 font-mono"
                        >
                          <span>{att.response_payload.short_url}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      att.status === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {att.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No external recovery attempt issued yet.</p>
            )}
          </div>

        </div>

      </div>
    </div>
  );
};
