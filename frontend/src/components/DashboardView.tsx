import React from 'react';
import {
  ArrowRight,
  CheckCircle2,
  History,
  Leaf,
  MessageSquare,
  Sparkles,
  TrendingUp,
  BarChart3,
  Layers,
} from 'lucide-react';
import type { DashboardStats, DiagnosisResult } from '../types';
import { AnimatedMarquee } from './AnimatedMarquee';

interface DashboardViewProps {
  stats: DashboardStats | null;
  currentAnalysis: DiagnosisResult | null;
  onNavigate: (tab: 'dashboard' | 'diagnose' | 'history' | 'query' | 'yield') => void;
  onSelectSample: (sampleId: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  stats,
  currentAnalysis,
  onNavigate,
  onSelectSample,
}) => {
  return (
    <div className="space-y-12 pb-16">
      {/* ─────────────────────────────────────────────────────────────────
          1. HERO SECTION
          ───────────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-8 pb-4">
        {/* Ambient glow backgrounds */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-gradient-to-tr from-emerald-200/40 via-teal-100/30 to-green-100/40 blur-3xl pointer-events-none rounded-full" />

        <div className="relative max-w-5xl mx-auto text-center px-4">
          {/* Top Pill Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs mb-6 hover:bg-emerald-100 transition-colors cursor-default">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
            <span>AI-Powered Agronomy</span>
            <span className="w-1 h-1 rounded-full bg-emerald-400" />
            <span className="font-bold text-emerald-900">99.67% Test Accuracy</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15] mb-6">
            Know your crop.{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-green-600">
              Protect your harvest.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-600 mb-8 leading-relaxed">
            Instant disease detection, automated severity estimation, actionable treatment plans,
            and harvest loss projections for <strong>Tomato</strong> and <strong>Potato</strong> growers.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={() => onNavigate('diagnose')}
              className="px-6 py-3.5 rounded-xl font-bold text-base bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 hover:bg-emerald-700 hover:shadow-emerald-600/40 active:scale-95 transition-all flex items-center gap-2.5 group cursor-pointer"
            >
              <Leaf className="w-5 h-5 group-hover:rotate-12 transition-transform" />
              <span>Analyze Leaf</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>

            <button
              onClick={() => onNavigate('query')}
              className="px-6 py-3.5 rounded-xl font-semibold text-base bg-white text-slate-700 border border-slate-200 shadow-xs hover:bg-slate-50 hover:text-slate-900 hover:border-slate-300 active:scale-95 transition-all flex items-center gap-2 cursor-pointer"
            >
              <MessageSquare className="w-5 h-5 text-emerald-600" />
              <span>Ask PlantCare</span>
            </button>
          </div>

          {/* Feature Highlights Under Hero */}
          <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto">
            <div className="p-3 rounded-xl bg-white/70 border border-slate-200/80 backdrop-blur-xs text-left shadow-2xs">
              <div className="flex items-center gap-2 text-emerald-700 font-semibold text-xs mb-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> 6 Disease Classes
              </div>
              <p className="text-xs text-slate-500">Early Blight, Late Blight & Healthy</p>
            </div>
            <div className="p-3 rounded-xl bg-white/70 border border-slate-200/80 backdrop-blur-xs text-left shadow-2xs">
              <div className="flex items-center gap-2 text-teal-700 font-semibold text-xs mb-1">
                <BarChart3 className="w-3.5 h-3.5" /> Severity Analysis
              </div>
              <p className="text-xs text-slate-500">Colorimetric lesion area %</p>
            </div>
            <div className="p-3 rounded-xl bg-white/70 border border-slate-200/80 backdrop-blur-xs text-left shadow-2xs">
              <div className="flex items-center gap-2 text-blue-700 font-semibold text-xs mb-1">
                <Layers className="w-3.5 h-3.5" /> Spray Engine
              </div>
              <p className="text-xs text-slate-500">Dosage, cultural & IPM guidance</p>
            </div>
            <div className="p-3 rounded-xl bg-white/70 border border-slate-200/80 backdrop-blur-xs text-left shadow-2xs">
              <div className="flex items-center gap-2 text-amber-700 font-semibold text-xs mb-1">
                <TrendingUp className="w-3.5 h-3.5" /> Yield Estimation
              </div>
              <p className="text-xs text-slate-500">Acreage baseline & loss models</p>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          2. ANIMATED MARQUEE IMAGE STRIP
          ───────────────────────────────────────────────────────────────── */}
      <AnimatedMarquee onSelectSample={onSelectSample} />

      {/* ─────────────────────────────────────────────────────────────────
          3. ACTIVE CURRENT ANALYSIS BANNER (IF LOADED)
          ───────────────────────────────────────────────────────────────── */}
      {currentAnalysis && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-900 via-slate-900 to-teal-950 p-6 sm:p-8 text-white shadow-xl border border-emerald-500/30">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  Active In-Session Diagnosis
                </div>
                <h3 className="text-2xl font-bold text-white tracking-tight">
                  {currentAnalysis.crop} —{' '}
                  <span
                    className={
                      currentAnalysis.is_healthy ? 'text-emerald-400' : 'text-amber-400'
                    }
                  >
                    {currentAnalysis.disease}
                  </span>
                </h3>
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300">
                  <span>
                    Prediction Confidence: <strong>{currentAnalysis.confidence}%</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Severity:{' '}
                    <strong className="text-white">{currentAnalysis.severity.level}</strong>
                  </span>
                  {currentAnalysis.severity.affected_percentage !== null && (
                    <>
                      <span>•</span>
                      <span>
                        Affected Area:{' '}
                        <strong>{currentAnalysis.severity.affected_percentage}%</strong>
                      </span>
                    </>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={() => onNavigate('diagnose')}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <Leaf className="w-4 h-4" />
                  View Diagnosis Details
                </button>
                <button
                  onClick={() => onNavigate('query')}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-colors flex items-center gap-1.5"
                >
                  <MessageSquare className="w-4 h-4" />
                  Ask About This
                </button>
                <button
                  onClick={() => onNavigate('yield')}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-colors flex items-center gap-1.5"
                >
                  <TrendingUp className="w-4 h-4" />
                  Calculate Yield
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          4. MAIN ACTION FEATURE CARDS (4-GRID)
          ───────────────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-8">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">PlantCare Core Suite</h2>
          <p className="text-sm text-slate-500 mt-1">
            Complete plant health management from leaf inspection to harvest projection
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1: Diagnose */}
          <div
            onClick={() => onNavigate('diagnose')}
            className="group relative rounded-2xl bg-white p-6 border border-slate-200/80 shadow-xs hover:shadow-xl hover:border-emerald-500/50 hover:-translate-y-1 transition-all duration-300 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Leaf className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">
                Analyze Leaf
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Upload or select a tomato/potato leaf photo for instantaneous EfficientNet-B0 disease
                classification and colorimetric lesion severity scoring.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-emerald-700">
              <span>Start Analysis</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Card 2: Ask PlantCare */}
          <div
            onClick={() => onNavigate('query')}
            className="group relative rounded-2xl bg-white p-6 border border-slate-200/80 shadow-xs hover:shadow-xl hover:border-teal-500/50 hover:-translate-y-1 transition-all duration-300 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <MessageSquare className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
                Ask PlantCare
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Specialized agronomic question-answering for blight management, spray intervals,
                organic preventions, and weather warnings.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-teal-700">
              <span>Ask a Question</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Card 3: Scan History */}
          <div
            onClick={() => onNavigate('history')}
            className="group relative rounded-2xl bg-white p-6 border border-slate-200/80 shadow-xs hover:shadow-xl hover:border-blue-500/50 hover:-translate-y-1 transition-all duration-300 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <History className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                Scan History
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Explore locally stored SQLite records of past field scans with confidence scores,
                severity metrics, and treatment summaries.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-blue-700">
              <span>View Past Scans</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          {/* Card 4: Yield Estimation */}
          <div
            onClick={() => onNavigate('yield')}
            className="group relative rounded-2xl bg-white p-6 border border-slate-200/80 shadow-xs hover:shadow-xl hover:border-amber-500/50 hover:-translate-y-1 transition-all duration-300 cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <TrendingUp className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 group-hover:text-amber-700 transition-colors">
                Yield Estimation
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Simulate potential harvest volume and disease loss based on cultivated acreage and
                active severity estimates with honest prototype metrics.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-amber-700">
              <span>Estimate Harvest</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          5. YOUR CROP HEALTH OVERVIEW (REAL SQLITE STATS)
          ───────────────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-2xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-xs">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Crop Health Overview</h2>
              <p className="text-xs text-slate-500">Live aggregate metrics queried from SQLite</p>
            </div>
            <button
              onClick={() => onNavigate('history')}
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
            >
              <span>Detailed History</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Stat 1 */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
              <span className="text-xs font-medium text-slate-500 block mb-1">Total Scans Stored</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                {stats ? stats.total_scans : '—'}
              </span>
              <span className="text-[11px] text-slate-400 block mt-1">In SQLite database</span>
            </div>

            {/* Stat 2 */}
            <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200/60">
              <span className="text-xs font-medium text-emerald-700 block mb-1">Healthy Samples</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-emerald-800">
                {stats ? stats.healthy_plants : '—'}
              </span>
              <span className="text-[11px] text-emerald-600 block mt-1">Zero pathogen detected</span>
            </div>

            {/* Stat 3 */}
            <div className="p-4 rounded-xl bg-rose-50/60 border border-rose-200/60">
              <span className="text-xs font-medium text-rose-700 block mb-1">Diseases Detected</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-rose-800">
                {stats ? stats.diseases_detected : '—'}
              </span>
              <span className="text-[11px] text-rose-600 block mt-1">Requiring treatment action</span>
            </div>

            {/* Stat 4 */}
            <div className="p-4 rounded-xl bg-teal-50/60 border border-teal-200/60">
              <span className="text-xs font-medium text-teal-700 block mb-1">Classifier Accuracy</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-teal-800">99.67%</span>
              <span className="text-[11px] text-teal-600 block mt-1">EfficientNet-B0 test score</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          6. RECENT SCANS TABLE (REAL SQLITE RECORDS)
          ───────────────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-2xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Recent Plant Scans</h2>
              <p className="text-xs text-slate-500">Last 5 field evaluations recorded in database</p>
            </div>
            <button
              onClick={() => onNavigate('history')}
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
            >
              <span>View All ({stats ? stats.total_scans : 0})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {stats && stats.recent_scans && stats.recent_scans.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-400 font-semibold uppercase tracking-wider">
                    <th className="pb-3 px-3">Crop</th>
                    <th className="pb-3 px-3">Disease Condition</th>
                    <th className="pb-3 px-3">Confidence</th>
                    <th className="pb-3 px-3">Severity</th>
                    <th className="pb-3 px-3">Date & Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {stats.recent_scans.map((scan) => (
                    <tr
                      key={scan.scan_id}
                      onClick={() => onNavigate('history')}
                      className="hover:bg-slate-50 transition-colors cursor-pointer"
                    >
                      <td className="py-3 px-3 font-semibold text-slate-900 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        {scan.crop}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded-full font-medium ${
                            scan.disease.toLowerCase() === 'healthy'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {scan.disease}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-600">
                        {scan.prediction_confidence.toFixed(1)}%
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded-md font-semibold text-[11px] ${
                            scan.severity === 'Severe'
                              ? 'bg-red-100 text-red-700'
                              : scan.severity === 'Moderate'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {scan.severity}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-400 font-mono">
                        {scan.timestamp ? scan.timestamp.substring(0, 16) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-10 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <Leaf className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-600">No scans recorded yet</p>
              <p className="text-xs text-slate-400 mt-1">
                Analyze your first leaf to save an entry to SQLite.
              </p>
              <button
                onClick={() => onNavigate('diagnose')}
                className="mt-4 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
              >
                Analyze Leaf Now
              </button>
            </div>
          )}
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          7. HOW PLANTCARE WORKS (5 STEPS)
          ───────────────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">How PlantCare Works</h2>
          <p className="text-sm text-slate-500 mt-1">
            An end-to-end intelligent diagnostic pipeline for modern smart agriculture
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm mb-3">
              1
            </div>
            <h4 className="text-sm font-bold text-slate-900">Upload Leaf</h4>
            <p className="text-xs text-slate-500 mt-1">
              Take or select a clear photo of an infected or healthy leaf
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center font-bold text-sm mb-3">
              2
            </div>
            <h4 className="text-sm font-bold text-slate-900">Classify Disease</h4>
            <p className="text-xs text-slate-500 mt-1">
              EfficientNet-B0 predicts specific crop & pathogen condition
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm mb-3">
              3
            </div>
            <h4 className="text-sm font-bold text-slate-900">Measure Severity</h4>
            <p className="text-xs text-slate-500 mt-1">
              Colorimetric segmentation calculates % surface lesion discoloration
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm mb-3">
              4
            </div>
            <h4 className="text-sm font-bold text-slate-900">Spray Guidance</h4>
            <p className="text-xs text-slate-500 mt-1">
              Actionable dosage, fungicides, cultural methods & weather rules
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-sm mb-3">
              5
            </div>
            <h4 className="text-sm font-bold text-slate-900">Track & Harvest</h4>
            <p className="text-xs text-slate-500 mt-1">
              Save to SQLite scan history and simulate yield impact
            </p>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────────
          8. SUPPORTED CROPS & PATHOGENS
          ───────────────────────────────────────────────────────────────── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 p-8 text-white shadow-xl">
          <div className="text-center max-w-2xl mx-auto mb-8">
            <h2 className="text-2xl font-bold tracking-tight text-white">Supported Crops & Pathogens</h2>
            <p className="text-xs text-slate-300 mt-1">
              Trained on validated solanaceous crops with laboratory and field test data
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Tomato Card */}
            <div className="rounded-xl bg-slate-800/80 border border-slate-700 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-red-500/20 text-red-400 flex items-center justify-center font-bold">
                      🍅
                    </div>
                    <div>
                      <h3 className="font-bold text-base text-white">Tomato (Solanum lycopersicum)</h3>
                      <p className="text-xs text-slate-400">Baseline Yield: 16.0 tons/acre</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    3 Conditions
                  </span>
                </div>

                <div className="space-y-2 mt-4 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60">
                    <span className="font-medium text-slate-200">Early Blight (Alternaria solani)</span>
                    <button
                      onClick={() => onSelectSample('tomato_early_blight')}
                      className="text-emerald-400 hover:underline"
                    >
                      Test Sample →
                    </button>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60">
                    <span className="font-medium text-slate-200">Late Blight (Phytophthora infestans)</span>
                    <button
                      onClick={() => onSelectSample('tomato_late_blight')}
                      className="text-emerald-400 hover:underline"
                    >
                      Test Sample →
                    </button>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60">
                    <span className="font-medium text-slate-200">Healthy Foliage</span>
                    <button
                      onClick={() => onSelectSample('tomato_healthy')}
                      className="text-emerald-400 hover:underline"
                    >
                      Test Sample →
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Potato Card */}
            <div className="rounded-xl bg-slate-800/80 border border-slate-700 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
                      🥔
                    </div>
                    <div>
                      <h3 className="font-bold text-base text-white">Potato (Solanum tuberosum)</h3>
                      <p className="text-xs text-slate-400">Baseline Yield: 12.0 tons/acre</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    3 Conditions
                  </span>
                </div>

                <div className="space-y-2 mt-4 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60">
                    <span className="font-medium text-slate-200">Early Blight (Alternaria solani)</span>
                    <button
                      onClick={() => onSelectSample('potato_early_blight')}
                      className="text-emerald-400 hover:underline"
                    >
                      Test Sample →
                    </button>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60">
                    <span className="font-medium text-slate-200">Late Blight (Phytophthora infestans)</span>
                    <button
                      onClick={() => onSelectSample('potato_late_blight')}
                      className="text-emerald-400 hover:underline"
                    >
                      Test Sample →
                    </button>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60">
                    <span className="font-medium text-slate-200">Healthy Foliage</span>
                    <button
                      onClick={() => onSelectSample('potato_healthy')}
                      className="text-emerald-400 hover:underline"
                    >
                      Test Sample →
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
