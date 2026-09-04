import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: string;
  color?: 'blue' | 'emerald' | 'amber' | 'purple' | 'red';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'blue',
}) => {
  const colorMap = {
    blue: 'from-blue-500/10 to-blue-600/5 text-blue-400 border-blue-500/20',
    emerald: 'from-emerald-500/10 to-emerald-600/5 text-emerald-400 border-emerald-500/20',
    amber: 'from-amber-500/10 to-amber-600/5 text-amber-400 border-amber-500/20',
    purple: 'from-purple-500/10 to-purple-600/5 text-purple-400 border-purple-500/20',
    red: 'from-red-500/10 to-red-600/5 text-red-400 border-red-500/20',
  };

  const iconBgMap = {
    blue: 'bg-blue-500/10 text-blue-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    amber: 'bg-amber-500/10 text-amber-400',
    purple: 'bg-purple-500/10 text-purple-400',
    red: 'bg-red-500/10 text-red-400',
  };

  return (
    <div className={`rounded-xl bg-gradient-to-br ${colorMap[color]} bg-[#131A29] p-5 border backdrop-blur-sm shadow-lg`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        <div className={`p-2 rounded-lg ${iconBgMap[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold text-white tracking-tight">{value}</div>
        {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        {trend && (
          <span className="inline-block mt-2 text-[11px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300">
            {trend}
          </span>
        )}
      </div>
    </div>
  );
};
