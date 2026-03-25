/**
 * TanStack Query hooks for the CMS Fraud Detection API.
 *
 * Wraps the raw API functions from `lib/api.ts` with useQuery/useMutation
 * so every page gets automatic caching, deduplication, background
 * refetching, and stale-while-revalidate behaviour.
 */

import { useQuery } from "@tanstack/react-query";
import {
  getDashboard,
  getHeatmap,
  getPendingCases,
  getProviders,
  getProviderDetail,
  getProviderScoreDetails,
  getProviderSignals,
  getProviderPeers,
  getProviderRadar,
  getProviderNetwork,
  getProviderExplain,
  getProviderGraph,
  getProviderCluster,
  getClaims,
  getClaim,
  getClaimScoreDetails,
  getCaseActions,
  getFairness,
  getValidation,
  getIngestStatus,
  getSourceVersions,
  getPipelineRuns,
} from "./api";

/* ── Query key factory ──────────────────────────────────────── */

export const queryKeys = {
  dashboard: ["dashboard"] as const,
  heatmap: ["dashboard", "heatmap"] as const,
  pendingCases: (limit: number) => ["cases", "pending", limit] as const,

  providers: (params: Record<string, unknown>) =>
    ["providers", params] as const,
  providerDetail: (npi: string) => ["providers", npi] as const,
  providerScoreDetails: (npi: string) =>
    ["providers", npi, "score-details"] as const,
  providerSignals: (npi: string) => ["providers", npi, "signals"] as const,
  providerPeers: (npi: string) => ["providers", npi, "peers"] as const,
  providerRadar: (npi: string) => ["providers", npi, "radar"] as const,
  providerNetwork: (npi: string) => ["providers", npi, "network"] as const,
  providerExplain: (npi: string) => ["providers", npi, "explain"] as const,
  providerGraph: (npi: string) => ["providers", npi, "graph"] as const,
  providerCluster: (npi: string) => ["providers", npi, "cluster"] as const,

  claims: (params: Record<string, unknown>) => ["claims", params] as const,
  claim: (caseId: string) => ["claims", caseId] as const,
  claimScoreDetails: (caseId: string) =>
    ["claims", caseId, "score-details"] as const,
  caseActions: (caseId: string) => ["cases", caseId, "actions"] as const,

  fairness: (params?: Record<string, unknown>) =>
    ["fairness", params ?? {}] as const,
  validation: ["validation"] as const,

  ingestStatus: ["ingest", "status"] as const,
  sourceVersions: ["ingest", "sources"] as const,
  pipelineRuns: ["ingest", "runs"] as const,
} as const;

/* ── Dashboard ──────────────────────────────────────────────── */

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: getDashboard,
  });
}

export function useHeatmap() {
  return useQuery({
    queryKey: queryKeys.heatmap,
    queryFn: getHeatmap,
  });
}

export function usePendingCases(limit = 10) {
  return useQuery({
    queryKey: queryKeys.pendingCases(limit),
    queryFn: () => getPendingCases(limit),
  });
}

/* ── Providers ──────────────────────────────────────────────── */

export function useProviders(params: {
  page?: number;
  per_page?: number;
  q?: string;
  state?: string;
  provider_type?: string;
  risk_band?: string;
}) {
  return useQuery({
    queryKey: queryKeys.providers(params),
    queryFn: () => getProviders(params),
    placeholderData: (prev) => prev,
  });
}

export function useProviderDetail(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerDetail(npi),
    queryFn: () => getProviderDetail(npi),
    enabled: !!npi,
  });
}

export function useProviderScoreDetails(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerScoreDetails(npi),
    queryFn: () => getProviderScoreDetails(npi),
    enabled: !!npi,
  });
}

export function useProviderSignals(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerSignals(npi),
    queryFn: () => getProviderSignals(npi),
    enabled: !!npi,
  });
}

export function useProviderPeers(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerPeers(npi),
    queryFn: () => getProviderPeers(npi),
    enabled: !!npi,
  });
}

export function useProviderRadar(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerRadar(npi),
    queryFn: () => getProviderRadar(npi),
    enabled: !!npi,
  });
}

export function useProviderNetwork(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerNetwork(npi),
    queryFn: () => getProviderNetwork(npi),
    enabled: !!npi,
  });
}

export function useProviderExplain(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerExplain(npi),
    queryFn: () => getProviderExplain(npi),
    enabled: !!npi,
  });
}

export function useProviderGraph(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerGraph(npi),
    queryFn: () => getProviderGraph(npi),
    enabled: !!npi,
  });
}

export function useProviderCluster(npi: string) {
  return useQuery({
    queryKey: queryKeys.providerCluster(npi),
    queryFn: () => getProviderCluster(npi),
    enabled: !!npi,
  });
}

/* ── Claims ─────────────────────────────────────────────────── */

export function useClaims(params: Record<string, unknown>) {
  return useQuery({
    queryKey: queryKeys.claims(params),
    queryFn: () =>
      getClaims(params as Parameters<typeof getClaims>[0]),
    placeholderData: (prev) => prev,
  });
}

export function useClaim(caseId: string) {
  return useQuery({
    queryKey: queryKeys.claim(caseId),
    queryFn: () => getClaim(caseId),
    enabled: !!caseId,
  });
}

export function useClaimScoreDetails(caseId: string) {
  return useQuery({
    queryKey: queryKeys.claimScoreDetails(caseId),
    queryFn: () => getClaimScoreDetails(caseId),
    enabled: !!caseId,
  });
}

export function useCaseActions(caseId: string) {
  return useQuery({
    queryKey: queryKeys.caseActions(caseId),
    queryFn: () => getCaseActions(caseId),
    enabled: !!caseId,
  });
}

/* ── Fairness & Validation ──────────────────────────────────── */

export function useFairness(params?: { threshold?: number; blind?: boolean }) {
  return useQuery({
    queryKey: queryKeys.fairness(params),
    queryFn: () => getFairness(params),
  });
}

export function useValidation() {
  return useQuery({
    queryKey: queryKeys.validation,
    queryFn: getValidation,
  });
}

/* ── Ingest / Data Management ───────────────────────────────── */

export function useIngestStatus() {
  return useQuery({
    queryKey: queryKeys.ingestStatus,
    queryFn: getIngestStatus,
  });
}

export function useSourceVersions() {
  return useQuery({
    queryKey: queryKeys.sourceVersions,
    queryFn: getSourceVersions,
  });
}

export function usePipelineRuns() {
  return useQuery({
    queryKey: queryKeys.pipelineRuns,
    queryFn: getPipelineRuns,
  });
}
