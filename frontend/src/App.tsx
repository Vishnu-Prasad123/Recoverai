import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { getHealthStatus } from './services/api';
import { HealthResponse } from './types';

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const data = await getHealthStatus();
      setHealth(data);
    } catch (err) {
      console.error('Failed to fetch backend health status:', err);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col font-sans">
      <Header health={health} loading={loading} onRefresh={fetchHealth} />
      
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Dashboard health={health} loading={loading} />
      </main>

      <footer className="border-t border-[#1E293B] bg-[#0F172A]/50 py-4 text-center text-xs text-slate-500">
        RecoverAI &copy; 2026 Razorpay Buildathon Submission — AI Revenue Recovery Track
      </footer>
    </div>
  );
}

export default App;
