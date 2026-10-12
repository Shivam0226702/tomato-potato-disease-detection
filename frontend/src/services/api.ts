import type {
  DashboardStats,
  DiagnosisResult,
  QueryResponse,
  SampleItem,
  ScanRecord,
  YieldEstimateResponse,
  InspectionRecord,
} from '../types';

const BASE_URL = '/api';

export async function fetchHealth(): Promise<{ status: string; device: string; classes: string[]; database: string }> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await fetch(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error(`Failed to fetch stats: ${res.statusText}`);
  return res.json();
}

export async function fetchSamples(): Promise<SampleItem[]> {
  const res = await fetch(`${BASE_URL}/samples`);
  if (!res.ok) throw new Error(`Failed to fetch samples: ${res.statusText}`);
  const data = await res.json();
  return data.samples || [];
}

export async function diagnoseFile(file: File): Promise<DiagnosisResult> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/diagnose`, {
      method: 'POST',
      body: formData,
    });
  } catch (netErr: any) {
    throw new Error(
      'Unable to connect to PlantCare backend. Please ensure the server is running on port 8000.'
    );
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Diagnosis failed (${res.status}): ${res.statusText}`);
  }

  const result: DiagnosisResult = await res.json();
  return result;
}

export async function diagnoseSample(sampleId: string): Promise<DiagnosisResult> {
  const res = await fetch(`${BASE_URL}/diagnose-sample/${sampleId}`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Sample diagnosis failed: ${res.statusText}`);
  }

  const result: DiagnosisResult = await res.json();
  return result;
}

export async function saveScanRecord(record: {
  crop: string;
  disease: string;
  prediction_confidence: number;
  severity: string;
  affected_area_percentage?: number | null;
  treatment_summary?: string;
  notes?: string;
}): Promise<{ success: boolean; scan_id: number }> {
  const res = await fetch(`${BASE_URL}/save-scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Save scan failed: ${res.statusText}`);
  }

  return res.json();
}

export async function fetchScanHistory(limit: number = 100): Promise<ScanRecord[]> {
  const res = await fetch(`${BASE_URL}/scans?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to fetch scan history: ${res.statusText}`);
  const data = await res.json();
  return data.scans || [];
}

export async function fetchScanById(id: number): Promise<ScanRecord> {
  const res = await fetch(`${BASE_URL}/scans/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch scan detail: ${res.statusText}`);
  const data = await res.json();
  return data.scan;
}

export async function clearScanHistory(): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${BASE_URL}/scans`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to clear history: ${res.statusText}`);
  return res.json();
}

export async function fetchAiStatus(): Promise<{
  is_configured: boolean;
  model: string;
  has_sdk: boolean;
}> {
  try {
    const res = await fetch(`${BASE_URL}/ai-status`);
    if (!res.ok) return { is_configured: false, model: 'gemini-3.5-flash', has_sdk: true };
    return res.json();
  } catch {
    return { is_configured: false, model: 'gemini-3.5-flash', has_sdk: true };
  }
}

export async function queryPlantCare(
  question: string,
  context?: Record<string, any>,
  history?: Array<{ role: string; text: string }>
): Promise<QueryResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, context, history }),
    });
  } catch (networkErr: any) {
    throw new Error(
      `Could not connect to the PlantCare server (${networkErr.message || 'connection failed'}). Please ensure the backend is running at http://127.0.0.1:8000 and try again.`
    );
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Query failed with status ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

export async function computeYieldEstimate(params: {
  crop: string;
  cultivated_area: number;
  area_unit: string;
  disease: string;
  severity: string;
}): Promise<YieldEstimateResponse> {
  const res = await fetch(`${BASE_URL}/yield-estimate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Yield estimate calculation failed: ${res.statusText}`);
  }

  return res.json();
}

export async function saveFieldInspection(
  formData: FormData
): Promise<{ success: boolean; inspection_id: number; inspection: InspectionRecord }> {
  const res = await fetch(`${BASE_URL}/inspections`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Save inspection failed: ${res.statusText}`);
  }

  return res.json();
}

export async function fetchFieldInspections(limit: number = 100): Promise<InspectionRecord[]> {
  const res = await fetch(`${BASE_URL}/inspections?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to fetch field inspections: ${res.statusText}`);
  const data = await res.json();
  return data.inspections || [];
}

export async function fetchFieldInspectionById(id: number): Promise<InspectionRecord> {
  const res = await fetch(`${BASE_URL}/inspections/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch inspection record: ${res.statusText}`);
  const data = await res.json();
  return data.inspection;
}

export async function diagnoseFieldInspection(
  id: number
): Promise<{ success: boolean; diagnosis: DiagnosisResult; inspection: InspectionRecord }> {
  const res = await fetch(`${BASE_URL}/inspections/${id}/diagnose`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Field diagnosis failed: ${res.statusText}`);
  }

  return res.json();
}

export async function deleteFieldInspection(
  id: number
): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${BASE_URL}/inspections/${id}`, {
    method: 'DELETE',
  });

  if (!res.ok) throw new Error(`Failed to delete inspection: ${res.statusText}`);
  return res.json();
}

