import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardView } from './components/DashboardView';
import { DiagnoseView } from './components/DiagnoseView';
import { HistoryView } from './components/HistoryView';
import { AskPlantCareView } from './components/AskPlantCareView';
import { YieldView } from './components/YieldView';
import { FieldInspectionView } from './components/FieldInspectionView';
import type { DashboardStats, DiagnosisResult, SampleItem } from './types';
import { fetchDashboardStats, fetchSamples, diagnoseSample } from './services/api';
import { Sprout } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<
    'dashboard' | 'diagnose' | 'history' | 'query' | 'yield' | 'field'
  >('dashboard');
  const [currentAnalysis, setCurrentAnalysis] = useState<DiagnosisResult | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [samples, setSamples] = useState<SampleItem[]>([]);

  // Load stats and sample items on mount
  const refreshStats = async () => {
    try {
      const data = await fetchDashboardStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load dashboard stats:', err);
    }
  };

  useEffect(() => {
    refreshStats();
    fetchSamples()
      .then((data) => setSamples(data))
      .catch((err) => console.error('Failed to load samples:', err));
  }, []);

  // Handler when user clicks a sample anywhere on dashboard or marquee
  const handleSelectSample = async (sampleId: string) => {
    setActiveTab('diagnose');
    try {
      const res = await diagnoseSample(sampleId);
      const matched = samples.find((s) => s.id === sampleId);
      if (matched) res.imageUrl = matched.image_url;
      setCurrentAnalysis(res);
    } catch (err) {
      console.error('Failed to analyze selected sample:', err);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Sticky Blurred Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentAnalysis={currentAnalysis}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {activeTab === 'dashboard' && (
          <DashboardView
            stats={stats}
            currentAnalysis={currentAnalysis}
            onNavigate={setActiveTab}
            onSelectSample={handleSelectSample}
          />
        )}

        {activeTab === 'diagnose' && (
          <DiagnoseView
            samples={samples}
            currentAnalysis={currentAnalysis}
            setCurrentAnalysis={setCurrentAnalysis}
            onNavigate={setActiveTab}
            onScanSaved={refreshStats}
          />
        )}

        {activeTab === 'history' && (
          <HistoryView onScanCountChange={refreshStats} />
        )}

        {activeTab === 'query' && (
          <AskPlantCareView currentAnalysis={currentAnalysis} />
        )}

        {activeTab === 'yield' && (
          <YieldView currentAnalysis={currentAnalysis} />
        )}

        {activeTab === 'field' && (
          <FieldInspectionView />
        )}
      </main>

      {/* Modern SaaS Footer */}
      <footer className="bg-white border-t border-slate-200/80 py-8 px-4 sm:px-6 lg:px-8 mt-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold">
              <Sprout className="w-3.5 h-3.5" />
            </div>
            <span className="font-bold text-slate-800">PlantCare</span>
            <span>— Smart Plant Health Assistant</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <span>EfficientNet-B0 (99.67% Test Acc)</span>
            <span>•</span>
            <span>SQLite Database</span>
            <span>•</span>
            <span>Tomato & Potato Solanaceae</span>
          </div>

          <div className="text-slate-400">
            College Technical Project • Stage 10 Frontend
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
