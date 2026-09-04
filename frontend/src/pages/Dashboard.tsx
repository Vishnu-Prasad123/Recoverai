import React, { useState, useEffect } from 'react';
import { HealthResponse, MetricsOverview, PaymentItem, PaymentFullDetail } from '../types';
import { getMetricsOverview, getPayments, getPaymentDetail, executeRecovery } from '../services/api';
import { ExecutiveMetrics } from '../components/ExecutiveMetrics';
import { RecoveryQueue } from '../components/RecoveryQueue';
import { PaymentDetailModal } from '../components/PaymentDetailModal';
import { Activity, RefreshCw, AlertCircle, ShieldCheck } from 'lucide-react';

interface DashboardProps {
  health: HealthResponse | null;
  loading: boolean;
}

export const Dashboard: React.FC<DashboardProps> = ({ health }) => {
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [payments, setPayments] = useState<PaymentItem[]>([]);
  const [loadingData, setLoadingData] = useState<boolean>(true);
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);
  const [paymentDetail, setPaymentDetail] = useState<PaymentFullDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setLoadingData(true);
    setErrorMessage(null);
    try {
      const [mRes, pRes] = await Promise.all([
        getMetricsOverview().catch(() => null),
        getPayments(1, 50).catch(() => ({ items: [], total: 0, page: 1, page_size: 50, total_pages: 0 }))
      ]);
      setMetrics(mRes);
      setPayments(pRes.items);
    } catch (err: any) {
      setErrorMessage('Failed to load live backend data. Please verify FastAPI backend is running on port 8000.');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleSelectPayment = async (paymentId: string) => {
    setSelectedPaymentId(paymentId);
    setLoadingDetail(true);
    try {
      const detail = await getPaymentDetail(paymentId);
      setPaymentDetail(detail);
    } catch (err: any) {
      console.error('Failed to load payment detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleRunRecovery = async (paymentId: string) => {
    setExecutingId(paymentId);
    try {
      await executeRecovery(paymentId);
      await loadDashboardData();
      if (selectedPaymentId === paymentId) {
        handleSelectPayment(paymentId);
      }
    } catch (err: any) {
      setErrorMessage(`Recovery Execution Failed: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setExecutingId(null);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      
      {/* Top Banner / Welcome Control Header */}
      <div className="rounded-2xl bg-gradient-to-r from-blue-950 via-[#131A29] to-cyan-950 border border-[#1E293B] p-6 shadow-xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-cyan-400 font-semibold text-xs uppercase tracking-wider mb-1">
              <Activity className="h-4 w-4 animate-pulse" />
              <span>Razorpay Buildathon 2026 — RecoverAI Operational Console</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Autonomous Revenue Recovery Control Center</h2>
            <p className="text-slate-400 text-sm mt-1 max-w-3xl">
              RecoverAI monitors failed transactions, calculates 0–100 recovery scores, recommends AI interventions, enforces 8 deterministic guardrails, and issues Razorpay Payment Links with live webhook synchronization.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadDashboardData}
              disabled={loadingData}
              className="bg-[#0B0F17] hover:bg-slate-800 text-slate-200 border border-[#1E293B] px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition shadow"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingData ? 'animate-spin' : ''}`} />
              <span>Refresh Data</span>
            </button>

            <div className="flex items-center space-x-2 text-xs font-mono bg-[#0B0F17]/90 px-3.5 py-2 rounded-xl border border-[#1E293B] text-slate-300">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>Guardrails: ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="bg-rose-900/30 border border-rose-500/40 rounded-xl p-4 text-xs font-mono text-rose-300 flex items-center space-x-3">
          <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Executive KPI Metrics */}
      <ExecutiveMetrics metrics={metrics} payments={payments} loading={loadingData} />

      {/* Recovery Queue */}
      <RecoveryQueue
        payments={payments}
        loading={loadingData}
        onSelectPayment={handleSelectPayment}
        onRunRecovery={handleRunRecovery}
        executingId={executingId}
      />

      {/* Payment Detail Modal */}
      {selectedPaymentId && (
        <PaymentDetailModal
          detail={paymentDetail}
          loading={loadingDetail}
          onClose={() => setSelectedPaymentId(null)}
          onRefresh={handleSelectPayment}
        />
      )}

    </div>
  );
};

export default Dashboard;
