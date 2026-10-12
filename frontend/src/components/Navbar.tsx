import React from 'react';
import { Sprout, Activity, History, MessageSquare, TrendingUp, Sparkles, Leaf, Compass } from 'lucide-react';
import type { DiagnosisResult } from '../types';

interface NavbarProps {
  activeTab: 'dashboard' | 'diagnose' | 'history' | 'query' | 'yield' | 'field';
  setActiveTab: (tab: 'dashboard' | 'diagnose' | 'history' | 'query' | 'yield' | 'field') => void;
  currentAnalysis: DiagnosisResult | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  currentAnalysis,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => setActiveTab('dashboard')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md shadow-emerald-500/20 group-hover:scale-105 transition-transform">
              <Sprout className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-xl text-slate-900 tracking-tight">PlantCare</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  <Sparkles className="w-3 h-3 mr-1 text-emerald-600" /> v2.0
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">Smart Plant Health Assistant</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'dashboard'
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <Activity className="w-4 h-4" />
              Dashboard
            </button>

            <button
              onClick={() => setActiveTab('diagnose')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'diagnose'
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <Leaf className="w-4 h-4" />
              Analyze Leaf
            </button>

            <button
              onClick={() => setActiveTab('query')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'query'
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              Ask PlantCare
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'history'
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <History className="w-4 h-4" />
              Scan History
            </button>

            <button
              onClick={() => setActiveTab('yield')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'yield'
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              Yield Estimation
            </button>

            <button
              onClick={() => setActiveTab('field')}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'field'
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
            >
              <Compass className="w-4 h-4" />
              Field AR
            </button>
          </nav>

          {/* Right Action & Active Context */}
          <div className="flex items-center gap-3">
            {currentAnalysis && (
              <button
                onClick={() => setActiveTab('diagnose')}
                className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200/80 hover:bg-amber-100 transition-colors"
                title="Active diagnosis in memory"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Active: <strong>{currentAnalysis.crop}</strong> ({currentAnalysis.disease})</span>
              </button>
            )}

            <button
              onClick={() => setActiveTab('diagnose')}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-emerald-600 text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 active:scale-95 transition-all flex items-center gap-2"
            >
              <Leaf className="w-4 h-4" />
              <span>Analyze Leaf</span>
            </button>
          </div>
        </div>

        {/* Mobile Navigation Row */}
        <div className="flex md:hidden items-center justify-around py-2 border-t border-slate-100 overflow-x-auto gap-2">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 ${
              activeTab === 'dashboard' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('diagnose')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 ${
              activeTab === 'diagnose' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600'
            }`}
          >
            Analyze
          </button>
          <button
            onClick={() => setActiveTab('query')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 ${
              activeTab === 'query' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600'
            }`}
          >
            Ask
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 ${
              activeTab === 'history' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600'
            }`}
          >
            History
          </button>
          <button
            onClick={() => setActiveTab('yield')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 ${
              activeTab === 'yield' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600'
            }`}
          >
            Yield
          </button>
          <button
            onClick={() => setActiveTab('field')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 ${
              activeTab === 'field' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600'
            }`}
          >
            Field AR
          </button>
        </div>
      </div>
    </header>
  );
};
