import React, { useState } from 'react';
import { PaymentItem } from '../types';
import { Search, Filter, ArrowUpDown, ChevronRight, Zap, RefreshCw, AlertOctagon, CheckCircle, ShieldAlert } from 'lucide-react';

interface RecoveryQueueProps {
  payments: PaymentItem[];
  loading: boolean;
  onSelectPayment: (paymentId: string) => void;
  onRunRecovery: (paymentId: string) => void;
  executingId: string | null;
}

export const RecoveryQueue: React.FC<RecoveryQueueProps> = ({
  payments,
  loading,
  onSelectPayment,
  onRunRecovery,
  executingId
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [methodFilter, setMethodFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'ev' | 'score' | 'amount'>('ev');

  // Filter Payments
  const filtered = payments.filter(p => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      if (!p.payment_id.toLowerCase().includes(term) && !p.customer_id.toLowerCase().includes(term)) {
        return false;
      }
    }
    if (statusFilter !== 'all' && p.status !== statusFilter) return false;
    if (methodFilter !== 'all' && p.payment_method !== methodFilter) return false;
    
    if (priorityFilter !== 'all') {
      const score = p.recovery_score ?? 50;
      if (priorityFilter === 'HIGH' && score < 70) return false;
      if (priorityFilter === 'MEDIUM' && (score < 40 || score >= 70)) return false;
      if (priorityFilter === 'LOW' && score >= 40) return false;
    }
    return true;
  });

  // Sort Payments
  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'ev') {
      const evA = a.expected_recovery_value ?? (a.amount * (a.recovery_probability ?? 0.5));
      const evB = b.expected_recovery_value ?? (b.amount * (b.recovery_probability ?? 0.5));
      return evB - evA;
    }
    if (sortBy === 'score') {
      return (b.recovery_score ?? 0) - (a.recovery_score ?? 0);
    }
    return b.amount - a.amount;
  });

  return (
    <div className="rounded-2xl bg-[#131A29] border border-[#1E293B] p-6 shadow-xl space-y-4">
      
      {/* Table Controls Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center space-x-2">
            <span>Prioritized Recovery Queue</span>
            <span className="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded-full font-mono">
              {sorted.length} Cases
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Failed payments prioritized by Expected Recovery Value (EV = Amount * P).
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search ID..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="bg-[#0B0F17] border border-[#1E293B] text-slate-200 text-xs pl-9 pr-3 py-2 rounded-xl focus:outline-none focus:border-blue-500 w-36 sm:w-48 font-mono"
            />
          </div>

          {/* Priority Filter */}
          <select
            value={priorityFilter}
            onChange={e => setPriorityFilter(e.target.value)}
            className="bg-[#0B0F17] border border-[#1E293B] text-slate-300 text-xs px-3 py-2 rounded-xl focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Priorities</option>
            <option value="HIGH">High Priority</option>
            <option value="MEDIUM">Medium Priority</option>
            <option value="LOW">Low Priority</option>
          </select>

          {/* Method Filter */}
          <select
            value={methodFilter}
            onChange={e => setMethodFilter(e.target.value)}
            className="bg-[#0B0F17] border border-[#1E293B] text-slate-300 text-xs px-3 py-2 rounded-xl focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Methods</option>
            <option value="upi">UPI</option>
            <option value="card">Card</option>
            <option value="netbanking">Netbanking</option>
          </select>

          {/* Sort By */}
          <button
            onClick={() => setSortBy(sortBy === 'ev' ? 'score' : sortBy === 'score' ? 'amount' : 'ev')}
            className="bg-[#0B0F17] border border-[#1E293B] text-slate-300 hover:text-white text-xs px-3 py-2 rounded-xl flex items-center space-x-1 font-mono transition"
          >
            <ArrowUpDown className="h-3.5 w-3.5 text-cyan-400" />
            <span className="uppercase">Sort: {sortBy}</span>
          </button>
        </div>
      </div>

      {/* Recovery Queue Table */}
      <div className="overflow-x-auto rounded-xl border border-[#1E293B]">
        <table className="w-full text-left text-xs text-slate-300 border-collapse">
          <thead className="bg-[#0B0F17] text-slate-400 font-semibold uppercase tracking-wider text-[10px] border-b border-[#1E293B]">
            <tr>
              <th className="py-3.5 px-4">Payment ID / Customer</th>
              <th className="py-3.5 px-4">Amount</th>
              <th className="py-3.5 px-4">Failure Reason</th>
              <th className="py-3.5 px-4">Recovery Score</th>
              <th className="py-3.5 px-4">Probability (P)</th>
              <th className="py-3.5 px-4">Expected Value (EV)</th>
              <th className="py-3.5 px-4">Guardrail Status</th>
              <th className="py-3.5 px-4">Status</th>
              <th className="py-3.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E293B]">
            {loading ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-slate-400 font-mono">
                  <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-400" />
                  Loading prioritized failed payments...
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-12 text-center text-slate-400">
                  No failed payments match the selected filter criteria.
                </td>
              </tr>
            ) : (
              sorted.map(p => {
                const score = p.recovery_score ?? 65.0;
                const prob = p.recovery_probability ?? 0.55;
                const ev = p.expected_recovery_value ?? (p.amount * prob);
                const isRecovered = p.status === 'RECOVERED';
                const isExecuting = executingId === p.payment_id;

                // Guardrail status evaluation preview
                const isBlock = p.previous_recovery_attempts >= 2;
                const isModify = p.amount >= 25000;

                return (
                  <tr
                    key={p.payment_id}
                    onClick={() => onSelectPayment(p.payment_id)}
                    className="hover:bg-[#1A2333] transition cursor-pointer group"
                  >
                    {/* Payment ID & Customer */}
                    <td className="py-3.5 px-4 font-mono">
                      <div className="font-semibold text-white group-hover:text-blue-400 transition">{p.payment_id}</div>
                      <div className="text-[11px] text-slate-400">{p.customer_id}</div>
                    </td>

                    {/* Amount */}
                    <td className="py-3.5 px-4 font-semibold text-white font-mono">
                      ₹{p.amount.toLocaleString('en-IN')}
                    </td>

                    {/* Failure Reason */}
                    <td className="py-3.5 px-4 capitalize text-slate-300">
                      <span className="bg-[#0B0F17] px-2 py-1 rounded border border-[#1E293B] text-[11px]">
                        {p.failure_reason.replace(/_/g, ' ')}
                      </span>
                    </td>

                    {/* Recovery Score */}
                    <td className="py-3.5 px-4 font-mono font-bold">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        score >= 70 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        score >= 40 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}>
                        {score.toFixed(1)}
                      </span>
                    </td>

                    {/* Recovery Probability */}
                    <td className="py-3.5 px-4 font-mono font-semibold text-cyan-400">
                      {(prob * 100).toFixed(1)}%
                    </td>

                    {/* Expected Recovery Value */}
                    <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                      ₹{ev.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>

                    {/* Guardrail Status Badge */}
                    <td className="py-3.5 px-4">
                      {isBlock ? (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                          <ShieldAlert className="h-3 w-3" />
                          <span>BLOCK</span>
                        </span>
                      ) : isModify ? (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                          <AlertOctagon className="h-3 w-3" />
                          <span>REVIEW</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          <CheckCircle className="h-3 w-3" />
                          <span>ALLOW</span>
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4 font-semibold text-[11px]">
                      <span className={`px-2 py-0.5 rounded-full ${
                        isRecovered ? 'bg-emerald-500/20 text-emerald-400' :
                        p.status === 'RECOVERY_INITIATED' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-slate-700 text-slate-300'
                      }`}>
                        {p.status}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="py-3.5 px-4 text-right" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={() => onRunRecovery(p.payment_id)}
                        disabled={isExecuting || isRecovered || isBlock}
                        className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition flex items-center space-x-1.5 ml-auto shadow-md ${
                          isRecovered
                            ? 'bg-emerald-500/10 text-emerald-400 cursor-default'
                            : isBlock
                            ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                            : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/20'
                        }`}
                      >
                        {isExecuting ? (
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Zap className="h-3.5 w-3.5" />
                        )}
                        <span>{isRecovered ? 'Recovered' : isBlock ? 'Blocked' : 'Run Recovery'}</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
};
