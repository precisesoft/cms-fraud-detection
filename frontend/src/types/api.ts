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

export interface HealthResponse {
  status: string;
  database: string;
  graph: string;
  version: string;
}
