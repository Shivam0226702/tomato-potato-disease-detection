import React, { useState, useEffect } from 'react';
import {
  History,
  Search,
  Trash2,
  Leaf,
  X,
  RefreshCw,
} from 'lucide-react';
import type { ScanRecord } from '../types';
import { fetchScanHistory, clearScanHistory } from '../services/api';

interface HistoryViewProps {
  onScanCountChange?: () => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ onScanCountChange }) => {
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [cropFilter, setCropFilter] = useState<'All' | 'Tomato' | 'Potato'>('All');
  const [statusFilter, setStatusFilter] = useState<'All' | 'Healthy' | 'Diseased'>('All');
  const [selectedScan, setSelectedScan] = useState<ScanRecord | null>(null);
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [showClearConfirm, setShowClearConfirm] = useState<boolean>(false);

  const loadScans = async () => {
    setIsLoading(true);
    try {
      const data = await fetchScanHistory(200);
      setScans(data);
    } catch (err) {
      console.error('Failed to load scan history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadScans();
  }, []);

  const handleClearHistory = async () => {
    setIsClearing(true);
    try {
      await clearScanHistory();
      setScans([]);
      setShowClearConfirm(false);
      if (onScanCountChange) onScanCountChange();
    } catch (err) {
      console.error('Failed to clear scan history:', err);
    } finally {
      setIsClearing(false);
    }
  };

  // Filtered scans
  const filteredScans = scans.filter((scan) => {
    const matchesSearch =
      scan.crop.toLowerCase().includes(searchTerm.toLowerCase()) ||
      scan.disease.toLowerCase().includes(searchTerm.toLowerCase()) ||
      scan.severity.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (scan.notes && scan.notes.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesCrop = cropFilter === 'All' || scan.crop === cropFilter;
    const isHealthy = scan.disease.toLowerCase() === 'healthy';
    const matchesStatus =
      statusFilter === 'All' ||
      (statusFilter === 'Healthy' && isHealthy) ||
      (statusFilter === 'Diseased' && !isHealthy);

    return matchesSearch && matchesCrop && matchesStatus;
  });

  const healthyCount = scans.filter((s) => s.disease.toLowerCase() === 'healthy').length;
  const diseasedCount = scans.length - healthyCount;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 mb-2">
            <History className="w-3.5 h-3.5 text-blue-600" />
            <span>SQLite Database: data/plant_health.db</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Scan History
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Browse and inspect all historical plant diagnosis evaluations stored locally.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadScans}
            className="px-3 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5 shadow-2xs"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          {scans.length > 0 && (
            <button
              onClick={() => setShowClearConfirm(true)}
              className="px-3 py-2 rounded-xl text-xs font-semibold bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100 transition-colors flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" /> Clear History
            </button>
          )}
        </div>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-xs font-medium text-slate-500 block">Total Recorded Scans</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">{scans.length}</span>
        </div>
        <div className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-200/60 shadow-2xs">
          <span className="text-xs font-medium text-emerald-700 block">Healthy Evaluations</span>
          <span className="text-2xl font-extrabold text-emerald-800 mt-1 block">{healthyCount}</span>
        </div>
        <div className="bg-amber-50/50 p-4 rounded-xl border border-amber-200/60 shadow-2xs">
          <span className="text-xs font-medium text-amber-700 block">Diseases Detected</span>
          <span className="text-2xl font-extrabold text-amber-800 mt-1 block">{diseasedCount}</span>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Search input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search crop, disease, or notes..."
            className="w-full pl-9 pr-3 py-2 rounded-lg text-xs bg-slate-50 border border-slate-200 focus:outline-none focus:border-emerald-500 focus:bg-white transition-colors"
          />
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs">
            <span className="text-slate-400 text-[11px] px-1 font-medium">Crop:</span>
            {(['All', 'Tomato', 'Potato'] as const).map((crop) => (
              <button
                key={crop}
                onClick={() => setCropFilter(crop)}
                className={`px-2 py-1 rounded-md text-xs font-semibold transition-colors ${
                  cropFilter === crop
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {crop}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs">
            <span className="text-slate-400 text-[11px] px-1 font-medium">Status:</span>
            {(['All', 'Healthy', 'Diseased'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-2 py-1 rounded-md text-xs font-semibold transition-colors ${
                  statusFilter === status
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Scans Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading SQLite records...
          </div>
        ) : filteredScans.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Crop</th>
                  <th className="py-3 px-4">Disease Condition</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Affected Area</th>
                  <th className="py-3 px-4">Treatment Summary</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredScans.map((scan) => (
                  <tr
                    key={scan.scan_id}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                    onClick={() => setSelectedScan(scan)}
                  >
                    <td className="py-3 px-4 font-mono text-slate-500">#{scan.scan_id}</td>
                    <td className="py-3 px-4 font-mono text-slate-500">
                      {scan.timestamp ? scan.timestamp.substring(0, 16) : '—'}
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-800">{scan.crop}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full font-semibold ${
                          scan.disease.toLowerCase() === 'healthy'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {scan.disease}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-slate-700">
                      {scan.prediction_confidence.toFixed(1)}%
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-md font-semibold text-[11px] ${
                          scan.severity === 'Severe'
                            ? 'bg-rose-100 text-rose-800'
                            : scan.severity === 'Moderate'
                            ? 'bg-amber-100 text-amber-800'
                            : scan.severity === 'Mild'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {scan.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600">
                      {scan.affected_area_percentage !== null
                        ? `${scan.affected_area_percentage}%`
                        : 'N/A'}
                    </td>
                    <td className="py-3 px-4 text-slate-500 max-w-xs truncate">
                      {scan.treatment_summary || '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedScan(scan);
                        }}
                        className="text-emerald-700 hover:text-emerald-800 font-semibold"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Leaf className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold text-slate-700">No matching scans found</p>
            <p className="text-slate-400 mt-1">Try adjusting your search terms or filters.</p>
          </div>
        )}
      </div>

      {/* Detailed Modal */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-slate-500">Scan #{selectedScan.scan_id}</span>
                <span className="w-1 h-1 rounded-full bg-slate-300" />
                <span className="text-xs text-slate-500">{selectedScan.timestamp}</span>
              </div>
              <button
                onClick={() => setSelectedScan(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Evaluated Target
              </span>
              <h3 className="text-xl font-extrabold text-slate-900 mt-1">
                {selectedScan.crop} —{' '}
                <span
                  className={
                    selectedScan.disease.toLowerCase() === 'healthy'
                      ? 'text-emerald-600'
                      : 'text-amber-600'
                  }
                >
                  {selectedScan.disease}
                </span>
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Prediction Confidence</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {selectedScan.prediction_confidence.toFixed(1)}%
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Severity Level</span>
                <span className="font-bold text-slate-900 text-sm">{selectedScan.severity}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Affected Surface Area</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {selectedScan.affected_area_percentage !== null
                    ? `${selectedScan.affected_area_percentage}%`
                    : 'N/A'}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Database Record</span>
                <span className="font-mono text-slate-900 text-sm">SQLite</span>
              </div>
            </div>

            {selectedScan.treatment_summary && (
              <div className="space-y-1.5 text-xs">
                <span className="font-bold text-slate-800 block">Treatment Recommendation Summary:</span>
                <p className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-slate-600 leading-relaxed">
                  {selectedScan.treatment_summary}
                </p>
              </div>
            )}

            {selectedScan.notes && (
              <div className="space-y-1 text-xs">
                <span className="font-bold text-slate-800 block">Notes / Metadata:</span>
                <p className="text-slate-500 italic">{selectedScan.notes}</p>
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedScan(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-colors"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Clear Confirmation Dialog */}
      {showClearConfirm && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-fade-in text-center">
            <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Clear All Scan Records?</h3>
            <p className="text-xs text-slate-500">
              This will erase all historical scan records from the local SQLite database. This action
              cannot be undone.
            </p>
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleClearHistory}
                disabled={isClearing}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 text-white hover:bg-rose-700 transition-colors"
              >
                {isClearing ? 'Clearing...' : 'Yes, Clear All'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
