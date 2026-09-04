import React from 'react';
import { ShieldCheck, Cpu, RefreshCw, AlertCircle } from 'lucide-react';
import { HealthResponse } from '../types';

interface HeaderProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, loading, onRefresh }) => {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="border-b border-[#1E293B] bg-[#0F172A]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
        
        {/* Brand & Track */}
        <div className="flex items-center space-x-4">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-400 p-0.5 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <div className="h-full w-full bg-[#0B0F17] rounded-[7px] flex items-center justify-center">
              <Cpu className="h-5 w-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold text-white tracking-tight">RecoverAI</h1>
              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Razorpay Buildathon 2026
              </span>
            </div>
            <p className="text-xs text-slate-400">Guardrail-Controlled Revenue Recovery Agent</p>
          </div>
        </div>

        {/* Backend Connectivity Status Badge */}
        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium bg-[#131A29] border border-[#1E293B]">
            {loading ? (
              <span className="flex items-center text-slate-400">
                <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1.5" />
                Connecting API...
              </span>
            ) : isHealthy ? (
              <span className="flex items-center text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse mr-2"></span>
                Backend Ready ({health?.database?.type?.toUpperCase() || 'SQLITE'})
              </span>
            ) : (
              <span className="flex items-center text-amber-400">
                <AlertCircle className="h-3.5 w-3.5 mr-1.5" />
                Backend Offline
              </span>
            )}
          </div>

          <button
            onClick={onRefresh}
            title="Refresh System Health"
            className="p-2 rounded-lg bg-[#131A29] hover:bg-[#1E293B] text-slate-400 hover:text-white transition border border-[#1E293B]"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="h-4 w-4" />
            <span>Guardrails Active</span>
          </div>
        </div>

      </div>
    </header>
  );
};
