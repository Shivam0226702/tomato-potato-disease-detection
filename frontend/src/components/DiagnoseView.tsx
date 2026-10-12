import React, { useState, useRef } from 'react';
import {
  Upload,
  Leaf,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Save,
  MessageSquare,
  TrendingUp,
  RefreshCw,
  ShieldAlert,
  Info,
  Check,
} from 'lucide-react';
import type { DiagnosisResult, SampleItem } from '../types';
import { diagnoseFile, diagnoseSample, saveScanRecord } from '../services/api';

interface DiagnoseViewProps {
  samples: SampleItem[];
  currentAnalysis: DiagnosisResult | null;
  setCurrentAnalysis: (res: DiagnosisResult | null) => void;
  onNavigate: (tab: 'dashboard' | 'diagnose' | 'history' | 'query' | 'yield') => void;
  onScanSaved: () => void;
}

/**
 * Safely normalizes guidance, management practices, or spray regimens
 * into a list of non-empty strings. Handles strings (paragraphs or bulleted lines),
 * arrays, objects, null, and undefined without throwing runtime errors.
 */
function normalizeGuidanceList(value: unknown): string[] {
  if (value === null || value === undefined) {
    return [];
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => (typeof item === 'string' ? item.trim() : String(item).trim()))
      .filter((item) => item.length > 0);
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return [];

    // If string has bullet points or multiple lines, split them
    if (trimmed.includes('\n')) {
      return trimmed
        .split('\n')
        .map((line) => line.replace(/^[\s•*-]+|\d+\.\s*/, '').trim())
        .filter((line) => line.length > 0);
    }

    return [trimmed];
  }

  if (typeof value === 'object') {
    return Object.values(value as Record<string, unknown>)
      .map((item) => (typeof item === 'string' ? item.trim() : String(item).trim()))
      .filter((item) => item.length > 0);
  }

  const str = String(value).trim();
  return str ? [str] : [];
}

export const DiagnoseView: React.FC<DiagnoseViewProps> = ({
  samples,
  currentAnalysis,
  setCurrentAnalysis,
  onNavigate,
  onScanSaved,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(
    currentAnalysis?.imageUrl || null
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // File validation helper
  const validateFile = (file: File): string | null => {
    const validExts = ['jpg', 'jpeg', 'png', 'webp'];
    const ext = file.name.split('.').pop()?.toLowerCase();
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp'];

    if (!validTypes.includes(file.type) && (!ext || !validExts.includes(ext))) {
      return 'Unsupported file format. Please upload a valid JPG, JPEG, PNG, or WEBP leaf photograph.';
    }

    if (file.size > 15 * 1024 * 1024) {
      return 'File size exceeds 15MB limit. Please upload a smaller image.';
    }

    if (file.size === 0) {
      return 'The selected file is empty. Please choose a valid image.';
    }

    return null;
  };

  // Handle Drag & Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileSelected(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      handleFileSelected(file);
    }
    // Clear input value so re-selecting the exact same file re-triggers onChange
    if (e.target) {
      e.target.value = '';
    }
  };

  const handleFileSelected = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setErrorMsg(validationError);
      setSelectedFile(null);
      return;
    }

    setErrorMsg(null);
    setSelectedFile(file);
    const localUrl = URL.createObjectURL(file);
    setPreviewUrl(localUrl);
    setSaveSuccess(false);
  };

  // Run analysis on selected file or active sample
  const handleAnalyze = async () => {
    if (!selectedFile && !previewUrl) {
      setErrorMsg('Please select or upload a leaf photo before analyzing.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    setSaveSuccess(false);

    try {
      let res: DiagnosisResult;
      if (selectedFile) {
        res = await diagnoseFile(selectedFile);
        res.imageUrl = previewUrl || undefined;
      } else if (currentAnalysis?.sample_id) {
        res = await diagnoseSample(currentAnalysis.sample_id);
        res.imageUrl = previewUrl || undefined;
      } else {
        throw new Error('No leaf image available to analyze. Please choose a file or sample.');
      }
      setCurrentAnalysis(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Diagnosis failed. Please check your image and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // One-click Sample Diagnosis
  const handleSelectSample = async (sample: SampleItem) => {
    setIsLoading(true);
    setErrorMsg(null);
    setSelectedFile(null);
    setPreviewUrl(sample.image_url);
    setSaveSuccess(false);

    try {
      const res = await diagnoseSample(sample.id);
      res.imageUrl = sample.image_url;
      setCurrentAnalysis(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to analyze sample image.');
    } finally {
      setIsLoading(false);
    }
  };

  // Save to SQLite
  const handleSaveToHistory = async () => {
    if (!currentAnalysis || isSaving || saveSuccess) return;
    setIsSaving(true);
    try {
      await saveScanRecord({
        crop: currentAnalysis.crop,
        disease: currentAnalysis.disease,
        prediction_confidence: currentAnalysis.confidence,
        severity: currentAnalysis.severity.level,
        affected_area_percentage: currentAnalysis.severity.affected_percentage,
        treatment_summary: currentAnalysis.treatment?.recommended_action || '',
        notes: `Analyzed via PlantCare Web App (${currentAnalysis.filename})`,
      });
      setSaveSuccess(true);
      onScanSaved();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save record to database.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setCurrentAnalysis(null);
    setErrorMsg(null);
    setSaveSuccess(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 mb-3">
          <Leaf className="w-3.5 h-3.5 text-emerald-600" />
          <span>Stage 5 + 6 Integrated Diagnostic Pipeline</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
          Leaf Health Diagnosis
        </h1>
        <p className="text-sm text-slate-600 mt-2">
          Upload a clear leaf photo or click one of the verified sample leaves below to detect disease,
          calculate visual lesion severity, and generate customized treatment instructions.
        </p>
      </div>

      {/* Main Grid: Upload Area on Left / Top, Results on Right / Bottom */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Dropzone, Analyze Action & Sample Picker (5 cols on lg) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Dropzone Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">
                Leaf Photo
              </h2>
              {previewUrl && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="text-xs font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3" /> Reset
                </button>
              )}
            </div>

            {/* Hidden File Input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/jpg,image/webp"
              className="hidden"
              onClick={(e) => e.stopPropagation()}
              onChange={handleFileChange}
            />

            {/* Drop / Preview Area */}
            {previewUrl ? (
              <div className="space-y-4">
                <div className="relative rounded-xl overflow-hidden bg-slate-900 border border-slate-200 flex items-center justify-center min-h-[220px] max-h-[300px]">
                  <img
                    src={previewUrl}
                    alt="Selected leaf"
                    className="max-h-[280px] w-auto max-w-full object-contain mx-auto"
                  />
                  <div className="absolute top-2 right-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-900/80 text-white hover:bg-slate-900 backdrop-blur-xs border border-white/20 transition-all flex items-center gap-1 shadow-xs cursor-pointer"
                    >
                      <Upload className="w-3 h-3" /> Change Photo
                    </button>
                  </div>
                </div>

                {/* File info badge */}
                {selectedFile && (
                  <div className="flex items-center justify-between text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-lg border border-slate-200/60 font-mono">
                    <span className="truncate max-w-[200px] font-medium text-slate-700">
                      {selectedFile.name}
                    </span>
                    <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
                  </div>
                )}

                {/* Prominent Primary Analyze Button */}
                <button
                  type="button"
                  onClick={handleAnalyze}
                  disabled={isLoading}
                  className="w-full py-3.5 px-4 rounded-xl text-sm font-bold bg-emerald-600 text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Analyzing Leaf Health...</span>
                    </>
                  ) : (
                    <>
                      <Leaf className="w-4 h-4" />
                      <span>Analyze Leaf Health</span>
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[240px] ${
                  isDragOver
                    ? 'border-emerald-500 bg-emerald-50/50 scale-[1.01]'
                    : 'border-slate-300 hover:border-emerald-400 hover:bg-slate-50/70 bg-slate-50/40'
                }`}
              >
                <div className="w-14 h-14 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto shadow-xs mb-3">
                  <Upload className="w-7 h-7" />
                </div>
                <p className="text-sm font-bold text-slate-800">
                  Drag & drop your leaf photo here
                </p>
                <p className="text-xs text-slate-500 mt-1 mb-4">
                  Supports JPG, JPEG, PNG, and WEBP (up to 15MB)
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white shadow-xs hover:bg-emerald-700 transition-colors cursor-pointer"
                >
                  Browse Files
                </button>
              </div>
            )}

            {/* Error Message */}
            {errorMsg && (
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 animate-fade-in">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                <span className="leading-relaxed font-medium">{errorMsg}</span>
              </div>
            )}
          </div>

          {/* Quick One-Click Samples */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>Quick Test Samples</span>
              </h3>
              <span className="text-[11px] text-slate-400">One-click test</span>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Select verified leaf images from our dataset to evaluate immediately:
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {samples.map((s) => (
                <button
                  key={s.id}
                  onClick={() => handleSelectSample(s)}
                  disabled={isLoading}
                  className="group p-2 rounded-xl border border-slate-200 hover:border-emerald-500 bg-slate-50 hover:bg-white text-left transition-all hover:shadow-sm cursor-pointer disabled:opacity-50"
                >
                  <img
                    src={s.image_url}
                    alt={s.name}
                    className="w-full h-16 object-cover rounded-lg mb-1.5 border border-slate-200/60"
                  />
                  <div className="text-[11px] font-bold text-slate-800 group-hover:text-emerald-700 line-clamp-1">
                    {s.crop}
                  </div>
                  <div className="text-[10px] text-slate-500 line-clamp-1">{s.condition}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Analysis Results (7 cols on lg) */}
        <div className="lg:col-span-7 space-y-6">
          {isLoading ? (
            <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center shadow-xs space-y-4">
              <div className="w-16 h-16 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin mx-auto" />
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Analyzing Leaf Health...
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Running EfficientNet-B0 inference, colorimetric lesion segmentation, and treatment rules
                </p>
              </div>
            </div>
          ) : currentAnalysis ? (
            <div className="space-y-6 animate-fade-in">
              {/* Card 1: Primary Diagnosis & Confidence */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs relative overflow-hidden">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
                      Crop & Pathogen Diagnosis
                    </span>
                    <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
                      <span>{currentAnalysis.crop}</span>
                      <span className="text-slate-400 font-normal">/</span>
                      <span
                        className={
                          currentAnalysis.is_healthy
                            ? 'text-emerald-600'
                            : 'text-amber-600'
                        }
                      >
                        {currentAnalysis.disease}
                      </span>
                    </h2>
                  </div>

                  <div className="text-left sm:text-right">
                    <span className="text-xs text-slate-500 block">Prediction Confidence</span>
                    <span className="text-2xl font-extrabold text-slate-900 font-mono">
                      {currentAnalysis.confidence.toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Unobtrusive Confidence Disclaimer */}
                <p className="text-[11px] text-slate-400 italic mt-2.5">
                  Confidence indicates the model&apos;s prediction score and does not guarantee
                  real-world diagnostic certainty.
                </p>
              </div>

              {/* Card 2: Visual Disease Severity */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <AlertTriangle
                      className={`w-4 h-4 ${
                        currentAnalysis.severity.level === 'Severe'
                          ? 'text-rose-600'
                          : currentAnalysis.severity.level === 'Moderate'
                          ? 'text-amber-600'
                          : 'text-emerald-600'
                      }`}
                    />
                    <span>Visual Disease Severity Estimation</span>
                  </h3>

                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide ${
                      currentAnalysis.severity.level === 'Severe'
                        ? 'bg-rose-100 text-rose-800'
                        : currentAnalysis.severity.level === 'Moderate'
                        ? 'bg-amber-100 text-amber-800'
                        : currentAnalysis.severity.level === 'Mild'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    {currentAnalysis.severity.level}
                  </span>
                </div>

                {/* Progress bar if affected_percentage is available */}
                {currentAnalysis.severity.affected_percentage !== null && (
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs font-semibold text-slate-700">
                      <span>Affected Leaf Surface Discoloration</span>
                      <span className="font-mono">
                        {currentAnalysis.severity.affected_percentage}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                      <div
                        className={`h-2.5 rounded-full transition-all duration-500 ${
                          currentAnalysis.severity.level === 'Severe'
                            ? 'bg-rose-600'
                            : currentAnalysis.severity.level === 'Moderate'
                            ? 'bg-amber-500'
                            : currentAnalysis.severity.level === 'Mild'
                            ? 'bg-yellow-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(4, currentAnalysis.severity.affected_percentage)
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Explanation text */}
                <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100">
                  {currentAnalysis.severity.explanation}
                </p>

                {/* Severity Disclaimer */}
                <p className="text-[11px] text-slate-400 italic">
                  {currentAnalysis.severity.disclaimer}
                </p>
              </div>

              {/* Card 3: Treatment & Management Guidance */}
              <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-emerald-600" />
                    <span>Actionable Treatment & Management Plan</span>
                  </h3>
                </div>

                {/* Immediate Action Banner */}
                {currentAnalysis.treatment?.recommended_action ? (
                  <div
                    className={`p-4 rounded-xl border text-xs leading-relaxed font-medium ${
                      currentAnalysis.is_healthy
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                        : currentAnalysis.severity?.level === 'Severe'
                        ? 'bg-rose-50 border-rose-200 text-rose-900'
                        : 'bg-amber-50 border-amber-200 text-amber-900'
                    }`}
                  >
                    <div className="font-bold text-sm mb-1">Recommended Immediate Action:</div>
                    {currentAnalysis.treatment.recommended_action}
                  </div>
                ) : null}

                {/* Cultural Practices */}
                {(() => {
                  const practices = normalizeGuidanceList(
                    currentAnalysis.treatment?.management_practices
                  );
                  if (practices.length === 0) return null;
                  return (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                        Cultural & Preventive Practices
                      </h4>
                      <ul className="space-y-1.5">
                        {practices.map((practice, idx) => (
                          <li key={idx} className="text-xs text-slate-600 flex items-start gap-2">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                            <span>{practice}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })()}

                {/* Chemical / Organic Treatment Guidance */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Treatment Guidance & Spray Regimen
                  </h4>
                  {(() => {
                    const guidanceItems = normalizeGuidanceList(
                      currentAnalysis.treatment?.treatment_guidance
                    );
                    if (guidanceItems.length === 0) {
                      return (
                        <p className="text-xs text-slate-400 italic">
                          No specific chemical treatment guidance required for this condition.
                        </p>
                      );
                    }
                    if (guidanceItems.length === 1) {
                      return (
                        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-700 leading-relaxed whitespace-pre-line">
                          {guidanceItems[0]}
                        </div>
                      );
                    }
                    return (
                      <ul className="space-y-1.5">
                        {guidanceItems.map((guide, idx) => (
                          <li key={idx} className="text-xs text-slate-600 flex items-start gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 flex-shrink-0 mt-1.5" />
                            <span>{guide}</span>
                          </li>
                        ))}
                      </ul>
                    );
                  })()}
                </div>

                {/* Professional Advice */}
                {currentAnalysis.treatment?.professional_advice && (
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-2">
                    <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-slate-800">Agronomist Consultation:</strong>{' '}
                      {currentAnalysis.treatment.professional_advice}
                    </div>
                  </div>
                )}

                {/* Treatment Disclaimer */}
                {currentAnalysis.treatment?.disclaimer && (
                  <p className="text-[11px] text-slate-400 italic">
                    {currentAnalysis.treatment.disclaimer}
                  </p>
                )}
              </div>

              {/* Action Buttons Row */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  onClick={handleSaveToHistory}
                  disabled={isSaving || saveSuccess}
                  className={`px-4 py-2.5 rounded-xl text-xs font-semibold shadow-xs transition-all flex items-center gap-2 cursor-pointer ${
                    saveSuccess
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : 'bg-emerald-600 text-white hover:bg-emerald-700'
                  }`}
                >
                  {saveSuccess ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-600" />
                      <span>Saved to SQLite History!</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      <span>{isSaving ? 'Saving...' : 'Save to Scan History'}</span>
                    </>
                  )}
                </button>

                <button
                  onClick={() => onNavigate('query')}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-2xs cursor-pointer"
                >
                  <MessageSquare className="w-4 h-4 text-teal-600" />
                  <span>Ask About This Diagnosis</span>
                </button>

                <button
                  onClick={() => onNavigate('yield')}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-2xs cursor-pointer"
                >
                  <TrendingUp className="w-4 h-4 text-amber-600" />
                  <span>Calculate Yield Impact</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200/80 p-12 text-center shadow-xs">
              <Leaf className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-800">
                Awaiting Leaf Input
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Upload a photo or select any of the curated test samples on the left to see the
                comprehensive diagnosis, severity assessment, and treatment plan.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
