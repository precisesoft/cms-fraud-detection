export type RiskBand = "stable" | "review" | "high_risk";

export interface Provider {
  npi: string;
  provider_name: string;
  provider_type: string;
  state: string;
  city: string;
  entity_code: string;
  max_seed_risk_score: number;
  risk_band: RiskBand;
  service_line_count: number;
  total_estimated_payment: number;
  revoked_2026: number;
}

export interface ProviderDetail extends Provider {
  enrolled_2025: number;
  total_services: number;
  total_benes: number;
  unique_hcpcs_codes: number;
  mean_submitted_charge: number;
  mean_payment_amt: number;
  service_hhi: number;
  top_code_share: number;
}

export interface Signal {
  signal_id: string;
  category: string;
  name: string;
  direction: string;
  value: number;
  detail: string;
  weight: number;
}

export interface PeerComparison {
  npi: string;
  provider_name: string;
  provider_type: string;
  state: string;
  risk_score: number;
  total_services: number;
  total_payment: number;
}

export interface Claim {
  case_id: string;
  hcpcs_cd: string;
  hcpcs_desc: string;
  tot_srvcs: number;
  tot_benes: number;
  avg_submitted_charge: number;
  avg_medicare_payment_amt: number;
  seed_risk_score: number;
  seed_case_label: string;
}

export interface ScoreResult {
  npi: string;
  provider_name: string;
  composite_score: number;
  risk_band: RiskBand;
  signals: Signal[];
}

export interface DashboardData {
  total_providers: number;
  total_cases: number;
  risk_distribution: {
    high_risk: number;
    review: number;
    stable: number;
  };
  top_providers: Provider[];
}

export interface HeatmapEntry {
  state: string;
  provider_count: number;
  high_risk_count: number;
  avg_risk_score: number;
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

export interface HealthResponse {
  status: string;
  database: string;
  graph: string;
  version: string;
}

export interface ProviderListResponse {
  data: Provider[];
  total: number;
  page: number;
  per_page: number;
}
