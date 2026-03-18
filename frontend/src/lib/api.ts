import type {
  Claim,
  DashboardData,
  GraphResponse,
  HeatmapEntry,
  HealthResponse,
  PeerComparison,
  ProviderDetail,
  ProviderListResponse,
  ScoreResult,
  Signal,
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

  dashboard: () => fetchApi<DashboardData>("/api/dashboard"),

  providers: (params?: {
    limit?: number;
    offset?: number;
    search?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return fetchApi<ProviderListResponse>(
      `/api/providers${qs ? `?${qs}` : ""}`,
    );
  },

  provider: (npi: string) => fetchApi<ProviderDetail>(`/api/providers/${npi}`),

  signals: (npi: string) => fetchApi<Signal[]>(`/api/providers/${npi}/signals`),

  peers: (npi: string) =>
    fetchApi<PeerComparison[]>(`/api/providers/${npi}/peers`),

  claims: (npi: string) => fetchApi<Claim[]>(`/api/providers/${npi}/claims`),

  score: (npi: string) => fetchApi<ScoreResult>(`/api/score/${npi}`),

  heatmap: () => fetchApi<HeatmapEntry[]>("/api/heatmap"),

  graph: (npi: string) => fetchApi<GraphResponse>(`/api/graph/${npi}`),
};
