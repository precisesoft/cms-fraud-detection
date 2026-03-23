/**
 * API client for the CMS Fraud Detection backend.
 * All calls target the deployed backend at VITE_API_BASE_URL.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

/* ── Auth token management ─────────────────────────────────── */

const TOKEN_KEY = "argus_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/* ── Core request helper ───────────────────────────────────── */

type JsonInit = Omit<RequestInit, "body"> & { body?: unknown };

async function request<T>(path: string, init?: JsonInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...init,
    headers,
    body: init?.body === undefined ? undefined : JSON.stringify(init.body),
  });

  if (response.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

/* ── Types matching OpenAPI schema ──────────────────────────── */

export type RiskBand = "stable" | "review" | "high_risk";
export type CaseAction = "APPROVED" | "FLAGGED" | "DENIED" | "ESCALATED";
export type Recommendation = "approve" | "review" | "deny";

export interface PaginationMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ProviderSummary {
  npi: string;
  provider_name: string | null;
  provider_type: string | null;
  state: string | null;
  city: string | null;
  entity_code: string | null;
  max_seed_risk_score: number | null;
  risk_band: RiskBand | null;
  service_line_count: number | null;
  total_estimated_payment: number | null;
  revoked_2026: number | null;
}

export interface ProviderListResponse {
  data: ProviderSummary[];
  meta: PaginationMeta;
}

export interface ProviderDetail {
  npi: string;
  provider_name: string | null;
  entity_code: string | null;
  city: string | null;
  state: string | null;
  zip5: string | null;
  provider_type: string | null;
  medicare_participating: string | null;
  enrolled_2025: number | null;
  revoked_2026: number | null;
  revocation_reason: string | null;
  service_line_count: number | null;
  total_services: number | null;
  total_benes: number | null;
  unique_hcpcs_codes: number | null;
  mean_submitted_charge: number | null;
  mean_payment_amt: number | null;
  total_estimated_payment: number | null;
  service_hhi: number | null;
  top_code_share: number | null;
  max_seed_risk_score: number | null;
  avg_seed_risk_score: number | null;
  n_high_risk_lines: number | null;
  risk_band: RiskBand | null;
  mean_volume_z: number | null;
  max_volume_z: number | null;
  mean_intensity_z: number | null;
  max_intensity_z: number | null;
  mean_charge_z: number | null;
  max_charge_z: number | null;
  mean_payment_z: number | null;
  max_payment_z: number | null;
  n_volume_outlier_lines: number | null;
  n_intensity_outlier_lines: number | null;
  n_charge_outlier_lines: number | null;
  top3_code_share: number | null;
  charge_cv: number | null;
  avg_benes_per_line: number | null;
  avg_services_per_line: number | null;
  avg_services_per_bene: number | null;
  [key: string]: unknown;
}

export interface Signal {
  name: string;
  category: string;
  direction: string;
  value: number | null;
  threshold: number | null;
  description: string;
}

export interface PeerLine {
  hcpcs_cd: string;
  hcpcs_desc: string | null;
  tot_srvcs: number | null;
  peer_avg_tot_srvcs: number | null;
  service_volume_peer_z: number | null;
  services_per_bene: number | null;
  services_per_bene_peer_z: number | null;
  submitted_to_allowed_ratio: number | null;
  submitted_to_allowed_peer_z: number | null;
  avg_medicare_payment_amt: number | null;
  payment_peer_z: number | null;
  peer_scope: string | null;
  peer_case_count: number | null;
  seed_risk_score: number | null;
  seed_case_label: string | null;
}

export interface PeerResponse {
  npi: string;
  lines: PeerLine[];
  total_lines: number;
}

export interface RadarDimension {
  dimension: string;
  provider: number;
  peer: number;
}

export interface RadarResponse {
  npi: string;
  dimensions: RadarDimension[];
}

export interface RiskDistribution {
  high_risk: number;
  review: number;
  stable: number;
}

export interface DashboardStats {
  total_providers: number;
  total_cases: number;
  risk_distribution: RiskDistribution;
  top_providers: ProviderSummary[];
}

export interface Claim {
  case_id: string;
  npi: string;
  provider_last_org_name: string | null;
  provider_first_name: string | null;
  provider_state: string | null;
  provider_type: string | null;
  hcpcs_cd: string;
  hcpcs_desc: string | null;
  tot_benes: number | null;
  tot_srvcs: number | null;
  avg_submitted_charge: number | null;
  avg_medicare_payment_amt: number | null;
  seed_risk_score: number | null;
  seed_case_label: string | null;
  [key: string]: unknown;
}

export interface ClaimListResponse {
  data: Claim[];
  meta: PaginationMeta;
}

export interface ClaimSimulationRequest {
  npi: string;
  hcpcs_cd: string;
  submitted_charge: number;
  num_services: number;
  num_benes: number;
  place_of_service?: string;
}

export interface PeerComparisonStats {
  metric: string;
  provider_value: number;
  peer_mean: number;
  z_score: number;
  percentile: number | null;
  peer_count: number;
}

export interface ClaimSimulationResult {
  npi: string;
  hcpcs_cd: string;
  risk_score: number;
  risk_band: RiskBand;
  recommendation: Recommendation;
  signals: Signal[];
  peer_comparisons: PeerComparisonStats[];
  provider_name: string | null;
  provider_type: string | null;
  state: string | null;
  narrative: string | null;
  anomaly_score: number | null;
}

export interface HeatmapEntry {
  state: string;
  provider_count: number;
  avg_risk_score: number;
  flagged_count: number;
}

export interface HeatmapResponse {
  data: HeatmapEntry[];
}

export interface CohortFairness {
  cohort: string;
  provider_count: number;
  flagged_count: number;
  flagging_rate: number;
  is_outlier: boolean;
}

export interface FairnessReport {
  by_state: CohortFairness[];
  by_specialty: CohortFairness[];
  overall_flagging_rate: number;
  statistical_parity_diff: number | null;
  disparate_impact_ratio: number | null;
  revocation_impact: RevocationImpact | null;
}

export interface RevocationImpact {
  overall_flagging_rate_with: number;
  overall_flagging_rate_without: number;
  flagging_rate_delta: number;
  disparate_impact_with: number | null;
  disparate_impact_without: number | null;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphResponse {
  npi: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NetworkNeighbor {
  npi: string;
  provider_name: string | null;
  provider_type: string | null;
  state: string | null;
  risk_score: number | null;
  revoked: boolean;
}

export interface NetworkRiskResponse {
  npi: string;
  zip5: string | null;
  same_zip_flagged: NetworkNeighbor[];
  same_org_flagged: NetworkNeighbor[];
  zip_risk_summary: Record<string, unknown> | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  sql: string | null;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  duration_ms: number;
  chart_spec: ChartSpec | null;
}

export interface ChartSpec {
  type: "bar" | "line" | "pie";
  title: string;
  xKey?: string;
  yKey?: string;
  nameKey?: string;
  valueKey?: string;
  data: Record<string, unknown>[];
}

export interface CaseActionRequest {
  action: CaseAction;
  notes?: string;
}

export interface CaseActionResponse {
  case_id: string;
  action: CaseAction;
  message: string;
}

export interface CaseActionRecord {
  id: number;
  case_id: string;
  npi: string;
  action: CaseAction;
  notes: string | null;
  analyst_id: string;
  created_at: string;
}

export interface CaseActionsListResponse {
  case_id: string;
  actions: CaseActionRecord[];
  current_status: CaseAction | null;
}

export interface PendingCase {
  case_id: string;
  npi: string;
  provider_last_org_name: string | null;
  hcpcs_cd: string;
  hcpcs_desc: string | null;
  seed_risk_score: number | null;
  seed_case_label: string | null;
  avg_submitted_charge: number | null;
  tot_srvcs: number | null;
  [key: string]: unknown;
}

export interface ScoreResult {
  npi: string;
  risk_score: number;
  legitimacy_score: number;
  risk_band: RiskBand;
  signals: Signal[];
  narrative: string | null;
  anomaly_score: number | null;
}

export interface HealthResponse {
  status: string;
  database: string;
  graph: string;
  version: string;
}

export interface DetectionByReason {
  reason: string;
  count: number;
  detected: number;
  rate: number;
}

export interface ValidationReport {
  overall_detection_rate: number;
  total_revoked_providers: number;
  total_revoked_cases: number;
  detection_by_reason: DetectionByReason[];
  baseline_flagging_rate: number;
  methodology: string;
}

/* ── API functions ──────────────────────────────────────────── */

export function getHealth() {
  return request<HealthResponse>("/health");
}

export function getDashboard() {
  return request<DashboardStats>("/api/dashboard");
}

export function getHeatmap() {
  return request<HeatmapResponse>("/api/dashboard/heatmap");
}

export function getProviders(params?: {
  page?: number;
  per_page?: number;
  q?: string;
  state?: string;
  provider_type?: string;
  risk_band?: string;
}) {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.per_page) search.set("per_page", String(params.per_page));
  if (params?.q) search.set("q", params.q);
  if (params?.state) search.set("state", params.state);
  if (params?.provider_type) search.set("provider_type", params.provider_type);
  if (params?.risk_band) search.set("risk_band", params.risk_band);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<ProviderListResponse>(`/api/providers${suffix}`);
}

export function getProviderDetail(npi: string) {
  return request<ProviderDetail>(`/api/providers/${npi}`);
}

export function getProviderSignals(npi: string) {
  return request<Signal[]>(`/api/providers/${npi}/signals`);
}

export function getProviderPeers(npi: string) {
  return request<PeerResponse>(`/api/providers/${npi}/peers`);
}

export function getProviderRadar(npi: string) {
  return request<RadarResponse>(`/api/providers/${npi}/radar`);
}

export function getProviderNetwork(npi: string) {
  return request<NetworkRiskResponse>(`/api/network/${npi}`);
}

export function getProviderGraph(npi: string) {
  return request<GraphResponse>(`/api/graph/${npi}`);
}

export function getClaims(params?: {
  page?: number;
  per_page?: number;
  npi?: string;
  case_label?: string;
  state?: string;
  provider_type?: string;
  risk_min?: number;
  risk_max?: number;
}) {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.per_page) search.set("per_page", String(params.per_page));
  if (params?.npi) search.set("npi", params.npi);
  if (params?.case_label) search.set("case_label", params.case_label);
  if (params?.state) search.set("state", params.state);
  if (params?.provider_type) search.set("provider_type", params.provider_type);
  if (params?.risk_min != null) search.set("risk_min", String(params.risk_min));
  if (params?.risk_max != null) search.set("risk_max", String(params.risk_max));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<ClaimListResponse>(`/api/claims${suffix}`);
}

export function getClaim(caseId: string) {
  return request<Claim>(`/api/claims/${encodeURIComponent(caseId)}`);
}

export function simulateClaim(payload: ClaimSimulationRequest) {
  return request<ClaimSimulationResult>("/api/claims/simulate", {
    method: "POST",
    body: payload,
  });
}

export function scoreClaim(payload: {
  npi: string;
  hcpcs_cd?: string;
  tot_srvcs?: number;
  avg_submitted_charge?: number;
}) {
  return request<ScoreResult>("/api/score", {
    method: "POST",
    body: payload,
  });
}

export function getFairness(params?: { threshold?: number; blind?: boolean }) {
  const search = new URLSearchParams();
  if (params?.threshold != null)
    search.set("threshold", String(params.threshold));
  if (params?.blind != null) search.set("blind", String(params.blind));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<FairnessReport>(`/api/fairness${suffix}`);
}

export function chat(message: string, history: ChatMessage[] = []) {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: { message, history },
  });
}

export function caseAction(caseId: string, action: CaseAction, notes?: string) {
  return request<CaseActionResponse>(`/api/cases/${caseId}/action`, {
    method: "POST",
    body: { action, notes },
  });
}

export function getCaseActions(caseId: string) {
  return request<CaseActionsListResponse>(`/api/cases/${caseId}/actions`);
}

export function getPendingCases(limit = 50) {
  return request<PendingCase[]>(`/api/cases/pending?limit=${limit}`);
}

export function getValidation() {
  return request<ValidationReport>("/api/validation");
}

/* ── Auth ──────────────────────────────────────────────────── */

export interface AuthUser {
  id: number;
  username: string;
  role: string;
  full_name: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export function login(username: string, password: string) {
  return request<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: { username, password },
  });
}

export function getMe() {
  return request<AuthUser>("/api/auth/me");
}
