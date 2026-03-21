export type RiskBand = "stable" | "review" | "high_risk";

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

export interface Signal {
  name: string;
  category: string;
  direction: string;
  value: number | null;
  threshold: number | null;
  description: string;
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

export type Recommendation = "approve" | "review" | "deny";

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
}

export interface ClaimListResponse {
  data: Claim[];
  meta: PaginationMeta;
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
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
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

export interface ChatResponse {
  answer: string;
  sql: string | null;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  duration_ms: number;
  chart_spec: ChartSpec | null;
}

export type CaseAction = "APPROVED" | "FLAGGED" | "DENIED" | "ESCALATED";

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
}

export interface HealthResponse {
  status: string;
  database: string;
  graph: string;
  version: string;
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
