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

export interface HealthResponse {
  status: string;
  database: string;
  graph: string;
  version: string;
}
