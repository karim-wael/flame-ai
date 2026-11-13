import {
  AssistantResponse,
  CompareResponse,
  DataSourceItem,
  Health,
  IngestionReport,
  InvestigationDetail,
  InvestigationSummary,
  ProvenanceRecord,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new Error(`Can't reach the FLARE API at ${API_BASE}. Check that the backend is running.`);
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : "";
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail || `The FLARE API returned an error (${res.status}).`);
  }
  return res.json() as Promise<T>;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface InvestigationFilters {
  source?: string;
  domain?: string;
  gravity?: string;
  search?: string;
}

export interface CompareBody {
  target_domain: string;
  target_gravity: string;
  oxygen_fraction: number;
  pressure_kpa: number;
  flow_velocity_cm_s: number;
  include_terrestrial_baseline: boolean;
  weights: { oxygen_fraction: number; pressure_kpa: number; flow_velocity_cm_s: number };
}

export interface AskBody {
  question: string;
  combustion_domain: string | null;
  gravity_regime: string | null;
  fuel_filter: string | null;
  top_k_chunks: number;
  top_k_experiments: number;
}

export const api = {
  health: () => request<Health>("/api/health"),
  sources: () => request<DataSourceItem[]>("/api/sources"),
  investigations: (f: InvestigationFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(f).forEach(([k, v]) => v && params.set(k, v));
    const qs = params.toString();
    return request<InvestigationSummary[]>(`/api/investigations${qs ? `?${qs}` : ""}`);
  },
  investigation: (id: string) => request<InvestigationDetail>(`/api/investigations/${encodeURIComponent(id)}`),
  compare: (body: CompareBody) => post<CompareResponse>("/api/compare", body),
  ask: (body: AskBody) => post<AssistantResponse>("/api/assistant/query", body),
  provenance: (id: string) => request<ProvenanceRecord>(`/api/provenance/${encodeURIComponent(id)}`),
  ingest: () => post<IngestionReport>("/api/ingestion/jobs", { source_filter: "ALL", force_refresh: true }),
};
