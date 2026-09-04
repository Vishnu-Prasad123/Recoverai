import React from 'react';
import { MetricsOverview, PaymentItem } from '../types';
import { MetricCard } from './MetricCard';
import { AlertTriangle, TrendingUp, CheckCircle2, DollarSign, Zap } from 'lucide-react';

interface ExecutiveMetricsProps {
  metrics: MetricsOverview | null;
  payments: PaymentItem[];
  loading: boolean;
}

export const ExecutiveMetrics: React.FC<ExecutiveMetricsProps> = ({ metrics, payments }) => {
  // Compute metrics from operational payment list & overview backend payload
  const totalFailed = metrics?.total_failed_payments || payments.length;
  const revenueAtRisk = metrics?.total_revenue_at_risk || payments.reduce((acc, p) => acc + p.amount, 0);

  // Compute Expected Recoverable Value from operational scoring
  const expectedRecoverable = payments.reduce((acc, p) => {
    if (p.expected_recovery_value) return acc + p.expected_recovery_value;
    const prob = p.recovery_probability ?? 0.5;
    return acc + (p.amount * prob);
  }, 0);

  // Operational recovered funds (only payments with status RECOVERED)
  const recoveredPayments = payments.filter(p => p.status === 'RECOVERED');
  const actualRecoveredRevenue = recoveredPayments.reduce((acc, p) => acc + p.amount, 0);

  // Recovery Rate
  const recoveryRate = totalFailed > 0 ? (recoveredPayments.length / totalFailed) * 100 : 0;
  
  // Pending action cases
  const actionRequiredCount = payments.filter(p => p.status === 'FAILED' || p.status === 'RECOVERY_INITIATED').length;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <MetricCard
        title="Revenue at Risk"
        value={`₹${revenueAtRisk.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
        subtitle={`From ${totalFailed} failed payments`}
        icon={AlertTriangle}
        color="red"
        trend="Active Failed Volume"
      />
      <MetricCard
        title="Expected Recoverable"
        value={`₹${expectedRecoverable.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
        subtitle="Prioritized Expected Value (EV)"
        icon={TrendingUp}
        color="amber"
        trend="Scoring Model Active"
      />
      <MetricCard
        title="Actual Recovered"
        value={`₹${actualRecoveredRevenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
        subtitle={`${recoveredPayments.length} verified recoveries`}
        icon={DollarSign}
        color="emerald"
        trend="Razorpay Test Mode"
      />
      <MetricCard
        title="Recovery Rate"
        value={`${recoveryRate.toFixed(1)}%`}
        subtitle="Verified outcome ratio"
        icon={CheckCircle2}
        color="purple"
        trend="Operational Sync"
      />
      <MetricCard
        title="Action Required"
        value={actionRequiredCount.toString()}
        subtitle="Cases ready for pipeline"
        icon={Zap}
        color="blue"
        trend="Guardrails Enforced"
      />
    </div>
  );
};
