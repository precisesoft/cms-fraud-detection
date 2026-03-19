import type {
  ClaimListResponse,
  ClaimSimulationRequest,
  ClaimSimulationResult,
  DashboardStats,
  FairnessReport,
  GraphResponse,
  HeatmapResponse,
  HealthResponse,
  PeerResponse,
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

async function postApi<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<TRes>;
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

  provider: (npi: string) => fetchApi<ProviderDetail>(`/api/providers/${npi}`),

  signals: (npi: string) => fetchApi<Signal[]>(`/api/providers/${npi}/signals`),

  peers: (npi: string) => fetchApi<PeerResponse>(`/api/providers/${npi}/peers`),

  claims: (params?: {
    page?: number;
    per_page?: number;
    npi?: string;
    case_label?: string;
    state?: string;
    risk_min?: number;
    risk_max?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.npi) query.set("npi", params.npi);
    if (params?.case_label) query.set("case_label", params.case_label);
    if (params?.state) query.set("state", params.state);
    if (params?.risk_min != null)
      query.set("risk_min", String(params.risk_min));
    if (params?.risk_max != null)
      query.set("risk_max", String(params.risk_max));
    const qs = query.toString();
    return fetchApi<ClaimListResponse>(`/api/claims${qs ? `?${qs}` : ""}`);
  },

  score: (npi: string) => fetchApi<ScoreResult>(`/api/score/${npi}`),

  heatmap: () => fetchApi<HeatmapResponse>("/api/dashboard/heatmap"),

  graph: (npi: string) => fetchApi<GraphResponse>(`/api/graph/${npi}`),

  fairness: () => fetchApi<FairnessReport>("/api/fairness"),

  simulateClaim: (req: ClaimSimulationRequest) =>
    postApi<ClaimSimulationRequest, ClaimSimulationResult>(
      "/api/claims/simulate",
      req,
    ),
};
