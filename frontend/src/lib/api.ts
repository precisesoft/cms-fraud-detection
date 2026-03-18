import type {
  ClaimListResponse,
  DashboardStats,
  GraphResponse,
  HeatmapResponse,
  HealthResponse,
  ProviderListResponse,
  ScoreResult,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetchApi<HealthResponse>("/health"),

  dashboard: () => fetchApi<DashboardStats>("/api/dashboard"),

  providers: (params?: {
    page?: number;
    per_page?: number;
    q?: string;
    state?: string;
    provider_type?: string;
    risk_band?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.q) query.set("q", params.q);
    if (params?.state) query.set("state", params.state);
    if (params?.provider_type) query.set("provider_type", params.provider_type);
    if (params?.risk_band) query.set("risk_band", params.risk_band);
    const qs = query.toString();
    return fetchApi<ProviderListResponse>(
      `/api/providers${qs ? `?${qs}` : ""}`,
    );
  },

  claims: (npi: string) =>
    fetchApi<ClaimListResponse>(`/api/providers/${npi}/claims`),

  score: (npi: string) => fetchApi<ScoreResult>(`/api/score/${npi}`),

  heatmap: () => fetchApi<HeatmapResponse>("/api/dashboard/heatmap"),

  graph: (npi: string) => fetchApi<GraphResponse>(`/api/graph/${npi}`),
};
