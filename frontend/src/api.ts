export type DiseaseId = "heart" | "diabetes" | "liver";

export interface Option { value: number; label: string }

export interface Feature {
  key: string;
  label: string;
  input: "number" | "select";
  kind: "numeric" | "categorical";
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  default: number;
  options?: Option[];
  normal?: [number | null, number | null];
  group: string;
  optional?: boolean;
  help?: string;
}

export interface DiseaseSummary {
  id: DiseaseId;
  name: string;
  tagline: string;
  dataset: string;
  n_features: number;
  model: string;
  accuracy: number;
  roc_auc: number;
  n_patients: number;
}

export interface LeaderboardRow {
  model: string;
  members?: string[];
  accuracy: number;
  roc_auc: number;
  roc_auc_std: number;
  f1: number;
  precision: number;
  recall: number;
  train_time_s: number;
}

export interface Meta {
  best_model: string;
  best_members: string[] | null;
  trained_at: string;
  cv_folds: number;
  leaderboard: LeaderboardRow[];
  holdout: {
    accuracy: number; roc_auc: number; f1: number; precision: number; recall: number;
    confusion_matrix: number[][];
    roc_curve: { fpr: number; tpr: number }[];
    n_test: number;
  };
  feature_importance: { feature: string; label: string; importance: number }[];
  cleaning: {
    rows_raw: number; rows_clean: number; n_features: number; positive_rate: number;
    class_counts: { positive: number; negative: number };
    missing_after_cleaning: Record<string, number>;
    steps: { action: string; detail: string; affected: number }[];
  };
  samples: { label: string; values: Record<string, number | null> }[];
}

export interface DiseaseDetail {
  id: DiseaseId;
  name: string;
  tagline: string;
  dataset: string;
  positive_label: string;
  negative_label: string;
  features: Feature[];
  risk_bands: [number, string][];
  meta: Meta;
}

export interface Contribution {
  feature: string; label: string; display: string; baseline_display: string; impact: number;
}

export interface Prediction {
  disease: DiseaseId;
  probability: number;
  risk_level: "low" | "moderate" | "high";
  prediction: string;
  advice: string;
  contributions: Contribution[];
  flags: { feature: string; label: string; status: "low" | "high"; value: string; range: string }[];
  imputed: string[];
  model: string;
  latency_ms: number;
}

export type Values = Record<string, number | null>;

export interface BatchRow {
  row: number;
  patient_id: string;
  values: Values;
  actual: 0 | 1 | null;
  errors: string[];
  probability?: number;
  risk_level?: "low" | "moderate" | "high";
  predicted?: 0 | 1;
  prediction?: string;
  top_factors?: Contribution[];
  flags?: string[];
  imputed?: string[];
}

export interface BatchResult {
  disease: DiseaseId;
  disease_name: string;
  auto_detected: boolean;
  filename: string;
  summary: {
    total: number; scored: number; errors: number;
    high: number; moderate: number; low: number;
    predicted_positive: number; mean_probability: number | null;
    labelled: number; agreement: number | null;
  };
  columns: {
    recognised: { column: string; feature: string }[];
    id_column: string | null;
    target_column: string | null;
    ignored: string[];
    not_provided: string[];
  };
  rows: BatchRow[];
  model: string;
  elapsed_ms: number;
}

export const fileUrl = (kind: "sample" | "template", id: DiseaseId, format: "csv" | "xlsx") =>
  `/api/${kind}/${id}?format=${format}`;

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  diseases: () => request<DiseaseSummary[]>("/api/diseases"),
  disease: (id: DiseaseId) => request<DiseaseDetail>(`/api/diseases/${id}`),
  predict: (id: DiseaseId, values: Values, signal?: AbortSignal) =>
    request<Prediction>(`/api/predict/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
      signal,
    }),
  batch: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<BatchResult>("/api/batch", { method: "POST", body });
  },
};
