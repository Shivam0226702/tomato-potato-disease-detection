import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Calculator,
} from 'lucide-react';
import type { DiagnosisResult, YieldEstimateResponse } from '../types';
import { computeYieldEstimate } from '../services/api';

interface YieldViewProps {
  currentAnalysis: DiagnosisResult | null;
}

export const YieldView: React.FC<YieldViewProps> = ({ currentAnalysis }) => {
  // Pre-fill state from active analysis if available
  const [crop, setCrop] = useState<string>(currentAnalysis?.crop || 'Tomato');
  const [disease, setDisease] = useState<string>(currentAnalysis?.disease || 'Early Blight');
  const [severity, setSeverity] = useState<string>(
    currentAnalysis?.severity.level || 'Moderate'
  );
  const [cultivatedArea, setCultivatedArea] = useState<number>(1.0);
  const [areaUnit, setAreaUnit] = useState<string>('acre');
  const [yieldResult, setYieldResult] = useState<YieldEstimateResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Update when currentAnalysis changes
  useEffect(() => {
    if (currentAnalysis) {
      setCrop(currentAnalysis.crop);
      setDisease(currentAnalysis.disease);
      setSeverity(currentAnalysis.severity.level);
    }
  }, [currentAnalysis]);

  const runCalculation = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await computeYieldEstimate({
        crop,
        cultivated_area: cultivatedArea,
        area_unit: areaUnit,
        disease,
        severity,
      });
      setYieldResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to compute yield estimation.');
    } finally {
      setIsLoading(false);
    }
  };

  // Re-calculate automatically when parameters change
  useEffect(() => {
    runCalculation();
  }, [crop, disease, severity, cultivatedArea, areaUnit]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 mb-2">
          <TrendingUp className="w-3.5 h-3.5 text-amber-600" />
          <span>Stage 9 Agricultural Harvest Projection</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Yield & Harvest Estimation
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Estimate potential farm harvest volume and assess loss impact using cultivated acreage and
          active visual disease severity.
        </p>
      </div>

      {/* Active Analysis Context Tag */}
      {currentAnalysis && (
        <div className="bg-emerald-50/80 border border-emerald-200/90 rounded-2xl p-4 text-xs text-emerald-900 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>
              <strong>Active Diagnosis Applied:</strong> {currentAnalysis.crop} (
              {currentAnalysis.disease}, {currentAnalysis.severity.level} Severity)
            </span>
          </div>
          <span className="text-[11px] text-emerald-700 hidden sm:inline">
            Confidence: {currentAnalysis.confidence.toFixed(1)}%
          </span>
        </div>
      )}

      {/* Main Grid: Parameters on Left, Responsive Metric Cards on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Parameter Form (5 cols on lg) */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-5">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Calculator className="w-4 h-4 text-emerald-600" />
            <span>Acreage & Crop Inputs</span>
          </h2>

          {/* Crop Selector */}
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1.5">Target Crop</label>
            <div className="grid grid-cols-2 gap-2">
              {['Tomato', 'Potato'].map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCrop(c)}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                    crop === c
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {c === 'Tomato' ? '🍅 Tomato' : '🥔 Potato'}
                </button>
              ))}
            </div>
          </div>

          {/* Disease Condition Selector */}
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1.5">Disease Condition</label>
            <div className="grid grid-cols-3 gap-2">
              {['Healthy', 'Early Blight', 'Late Blight'].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDisease(d)}
                  className={`py-2 px-2 rounded-xl text-[11px] font-semibold border transition-all truncate ${
                    disease === d
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Severity Level Selector */}
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1.5">Severity Level</label>
            <div className="grid grid-cols-4 gap-1.5">
              {['None (Healthy)', 'Mild', 'Moderate', 'Severe'].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSeverity(s)}
                  className={`py-2 px-1 rounded-xl text-[10px] font-semibold border transition-all truncate ${
                    severity === s
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {s.replace(' (Healthy)', '')}
                </button>
              ))}
            </div>
          </div>

          {/* Area Unit & Cultivated Area */}
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700">Cultivated Farm Area</label>
              <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-xs">
                {(['acre', 'hectare'] as const).map((unit) => (
                  <button
                    key={unit}
                    type="button"
                    onClick={() => setAreaUnit(unit)}
                    className={`px-2.5 py-0.5 rounded-md font-semibold text-xs capitalize transition-colors ${
                      areaUnit === unit
                        ? 'bg-white text-slate-900 shadow-2xs'
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    {unit}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="100.0"
                value={cultivatedArea}
                onChange={(e) => setCultivatedArea(Math.max(0.1, parseFloat(e.target.value) || 0.1))}
                className="w-24 px-3 py-2 text-sm font-mono font-bold bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-emerald-500"
              />
              <input
                type="range"
                min="0.1"
                max="20.0"
                step="0.1"
                value={cultivatedArea}
                onChange={(e) => setCultivatedArea(parseFloat(e.target.value))}
                className="flex-1 accent-emerald-600"
              />
              <span className="text-xs font-semibold text-slate-500">
                {cultivatedArea.toFixed(1)} {areaUnit}
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: 2x2 Responsive Metric Cards & Scientific Disclaimer (7 cols on lg) */}
        <div className="lg:col-span-7 space-y-6">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
              {errorMsg}
            </div>
          )}
          {isLoading && !yieldResult && (
            <div className="p-8 text-center text-xs text-slate-400">
              Calculating yield baseline...
            </div>
          )}
          {yieldResult && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Card 1: Estimated Yield Per Unit Area */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">
                    Estimated Yield
                  </span>
                  <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 font-mono">
                    {yieldResult.estimated_yield_kg_per_unit.toLocaleString()} kg/{yieldResult.area_unit}
                  </div>
                  <div className="text-sm font-semibold text-slate-500 mt-1">
                    ({yieldResult.estimated_yield_per_unit.toFixed(1)} tons/{yieldResult.area_unit})
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400">
                  Baseline healthy:{' '}
                  {yieldResult.crop === 'Tomato' ? '16.0 tons/acre' : '12.0 tons/acre'}
                </div>
              </div>

              {/* Card 2: Estimated Total Harvest */}
              <div className="bg-emerald-50/50 rounded-2xl border border-emerald-200/70 p-5 shadow-xs flex flex-col justify-between">
                <div>
                  <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider block mb-1">
                    Estimated Total Harvest
                  </span>
                  <div className="text-2xl sm:text-3xl font-extrabold text-emerald-900 font-mono">
                    {yieldResult.estimated_total_yield_kg.toLocaleString()} kg
                  </div>
                  <div className="text-sm font-semibold text-emerald-700 mt-1">
                    ({yieldResult.estimated_total_yield.toFixed(1)} tons total)
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-emerald-200/50 text-[11px] text-emerald-700">
                  Across {yieldResult.cultivated_area} {yieldResult.area_unit}
                </div>
              </div>

              {/* Card 3: Expected Harvest Range */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">
                    Expected Harvest Range
                  </span>
                  <div className="text-xl sm:text-2xl font-extrabold text-slate-900 font-mono">
                    {yieldResult.range_min_kg.toLocaleString()} – {yieldResult.range_max_kg.toLocaleString()} kg
                  </div>
                  <div className="text-sm font-semibold text-slate-500 mt-1">
                    ({yieldResult.range_min.toFixed(1)} – {yieldResult.range_max.toFixed(1)} tons)
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-400">
                  ±15% variance based on field variables
                </div>
              </div>

              {/* Card 4: Disease Impact & Loss Reduction */}
              <div
                className={`rounded-2xl border p-5 shadow-xs flex flex-col justify-between ${
                  yieldResult.loss_percentage > 0
                    ? 'bg-rose-50/50 border-rose-200/70'
                    : 'bg-emerald-50/50 border-emerald-200/70'
                }`}
              >
                <div>
                  <span
                    className={`text-xs font-bold uppercase tracking-wider block mb-1 ${
                      yieldResult.loss_percentage > 0 ? 'text-rose-700' : 'text-emerald-700'
                    }`}
                  >
                    Disease Impact
                  </span>
                  <div
                    className={`text-2xl sm:text-3xl font-extrabold tracking-tight ${
                      yieldResult.loss_percentage > 0 ? 'text-rose-900' : 'text-emerald-900'
                    }`}
                  >
                    {yieldResult.impact_category}
                  </div>
                  <div
                    className={`text-sm font-semibold mt-1 ${
                      yieldResult.loss_percentage > 0 ? 'text-rose-700' : 'text-emerald-700'
                    }`}
                  >
                    Assumed yield reduction: {yieldResult.loss_percentage}%
                  </div>
                </div>
                <div
                  className={`mt-4 pt-3 border-t text-[11px] ${
                    yieldResult.loss_percentage > 0
                      ? 'border-rose-200/50 text-rose-600'
                      : 'border-emerald-200/50 text-emerald-600'
                  }`}
                >
                  {yieldResult.loss_percentage > 0
                    ? 'Early spray intervention can mitigate loss'
                    : 'Full yield potential maintained'}
                </div>
              </div>
            </div>
          )}

          {/* Prominent Scientific Prototype Disclaimer */}
          <div className="bg-amber-50/80 border border-amber-300 rounded-2xl p-5 text-amber-950 text-xs leading-relaxed space-y-2">
            <div className="flex items-center gap-2 font-bold text-amber-900">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span>Scientific & Prototype Notice:</span>
            </div>
            <p className="text-amber-900/90">{yieldResult?.disclaimer}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
