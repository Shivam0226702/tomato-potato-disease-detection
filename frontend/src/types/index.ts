export interface TopPrediction {
  crop: string;
  disease: string;
  label: string;
  confidence: number;
}

export interface SeverityDetail {
  level: string; // 'Mild' | 'Moderate' | 'Severe' | 'None (Healthy)' | 'Uncertain'
  affected_percentage: number | null;
  is_reliable: boolean;
  status_color: string;
  summary: string;
  explanation: string;
  disclaimer: string;
}

export interface TreatmentDetail {
  recommended_action: string;
  management_practices: string[] | string;
  treatment_guidance: string | string[];
  professional_advice: string;
  disclaimer: string;
}

export interface DefaultYieldDetail {
  crop: string;
  cultivated_area: number;
  area_unit: string;
  estimated_yield_per_unit: number;
  estimated_yield_kg_per_unit: number;
  estimated_total_yield: number;
  estimated_total_yield_kg: number;
  range_min: number;
  range_max: number;
  range_min_kg: number;
  range_max_kg: number;
  loss_percentage: number;
  impact_category: string;
  disclaimer: string;
}

export interface DiagnosisResult {
  success: boolean;
  filename: string;
  crop: string;
  disease: string;
  confidence: number;
  is_healthy: boolean;
  top_predictions: TopPrediction[];
  severity: SeverityDetail;
  treatment: TreatmentDetail;
  default_yield: DefaultYieldDetail;
  imageUrl?: string;
  sample_id?: string;
}

export interface ScanRecord {
  scan_id: number;
  timestamp: string;
  crop: string;
  disease: string;
  prediction_confidence: number;
  severity: string;
  affected_area_percentage: number | null;
  treatment_summary: string;
  notes: string;
}

export interface DashboardStats {
  total_scans: number;
  healthy_plants: number;
  diseases_detected: number;
  disease_distribution: Record<string, number>;
  crop_distribution: Record<string, number>;
  recent_scans: ScanRecord[];
}

export interface SampleItem {
  id: string;
  name: string;
  crop: string;
  condition: string;
  image_url: string;
}

export interface QueryResponse {
  answer: string;
  crop: string;
  disease: string;
  sources?: string[];
  disclaimer?: string;
  is_ai?: boolean;
  model?: string;
  error?: string;
}

export interface YieldEstimateResponse {
  crop: string;
  cultivated_area: number;
  area_unit: string;
  disease: string;
  severity: string;
  baseline_yield_per_acre: number;
  estimated_yield_per_unit: number;
  estimated_yield_kg_per_unit: number;
  estimated_total_yield: number;
  estimated_total_yield_kg: number;
  range_min: number;
  range_max: number;
  range_min_kg: number;
  range_max_kg: number;
  loss_percentage: number;
  impact_category: string;
  disclaimer: string;
}

export interface InspectionRecord {
  inspection_id: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  gps_accuracy: number;
  image_url: string;
  overlay_image_url?: string | null;
  field_name?: string;
  notes?: string;
  crop?: string | null;
  disease?: string | null;
  prediction_confidence?: number | null;
  severity?: string | null;
  affected_area_percentage?: number | null;
  treatment_summary?: string | null;
}
