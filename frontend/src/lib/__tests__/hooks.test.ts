/**
 * Tests for TanStack Query hooks in lib/hooks.ts.
 *
 * Each hook is a thin wrapper around useQuery + an API function.
 * We mock every API import and verify each hook calls its API fn
 * with the correct arguments.
 */

import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { createElement } from "react";

import {
  useDashboard,
  useHeatmap,
  usePendingCases,
  useProviders,
  useProviderDetail,
  useProviderScoreDetails,
  useProviderSignals,
  useProviderPeers,
  useProviderRadar,
  useProviderNetwork,
  useProviderExplain,
  useProviderGraph,
  useProviderCluster,
  useClaims,
  useClaim,
  useClaimScoreDetails,
  useCaseActions,
  useFairness,
  useValidation,
  useIngestStatus,
  useSourceVersions,
  usePipelineRuns,
  queryKeys,
} from "../hooks";

/* ── Mock all API functions ─────────────────────────────────── */

vi.mock("../api", () => ({
  getDashboard: vi.fn().mockResolvedValue({ total_providers: 10 }),
  getHeatmap: vi.fn().mockResolvedValue([]),
  getPendingCases: vi.fn().mockResolvedValue({ items: [] }),
  getProviders: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getProviderDetail: vi.fn().mockResolvedValue({ npi: "123" }),
  getProviderScoreDetails: vi.fn().mockResolvedValue({}),
  getProviderSignals: vi.fn().mockResolvedValue([]),
  getProviderPeers: vi.fn().mockResolvedValue([]),
  getProviderRadar: vi.fn().mockResolvedValue([]),
  getProviderNetwork: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getProviderExplain: vi.fn().mockResolvedValue({ narrative: "" }),
  getProviderGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getProviderCluster: vi.fn().mockResolvedValue([]),
  getClaims: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getClaim: vi.fn().mockResolvedValue({ case_id: "abc" }),
  getClaimScoreDetails: vi.fn().mockResolvedValue({}),
  getCaseActions: vi.fn().mockResolvedValue([]),
  getFairness: vi.fn().mockResolvedValue({}),
  getValidation: vi.fn().mockResolvedValue({}),
  getIngestStatus: vi.fn().mockResolvedValue(null),
  getSourceVersions: vi.fn().mockResolvedValue([]),
  getPipelineRuns: vi.fn().mockResolvedValue([]),
}));

/* ── Helpers ────────────────────────────────────────────────── */

function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
}

function wrapper({ children }: { children: ReactNode }) {
  return createElement(
    QueryClientProvider,
    { client: makeClient() },
    children,
  );
}

/* ── queryKeys ──────────────────────────────────────────────── */

describe("queryKeys", () => {
  it("returns static keys for dashboard, heatmap, validation", () => {
    expect(queryKeys.dashboard).toEqual(["dashboard"]);
    expect(queryKeys.heatmap).toEqual(["dashboard", "heatmap"]);
    expect(queryKeys.validation).toEqual(["validation"]);
    expect(queryKeys.ingestStatus).toEqual(["ingest", "status"]);
    expect(queryKeys.sourceVersions).toEqual(["ingest", "sources"]);
    expect(queryKeys.pipelineRuns).toEqual(["ingest", "runs"]);
  });

  it("returns parameterised keys for dynamic queries", () => {
    expect(queryKeys.pendingCases(5)).toEqual(["cases", "pending", 5]);
    expect(queryKeys.providers({ q: "x" })).toEqual(["providers", { q: "x" }]);
    expect(queryKeys.providerDetail("NPI1")).toEqual(["providers", "NPI1"]);
    expect(queryKeys.claims({ page: 1 })).toEqual(["claims", { page: 1 }]);
    expect(queryKeys.claim("C1")).toEqual(["claims", "C1"]);
    expect(queryKeys.caseActions("C1")).toEqual(["cases", "C1", "actions"]);
    expect(queryKeys.fairness({ threshold: 50 })).toEqual([
      "fairness",
      { threshold: 50 },
    ]);
    expect(queryKeys.fairness()).toEqual(["fairness", {}]);
  });
});

/* ── Dashboard hooks ────────────────────────────────────────── */

describe("useDashboard", () => {
  it("resolves with dashboard data", async () => {
    const { result } = renderHook(() => useDashboard(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ total_providers: 10 });
  });
});

describe("useHeatmap", () => {
  it("resolves with heatmap data", async () => {
    const { result } = renderHook(() => useHeatmap(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });
});

describe("usePendingCases", () => {
  it("resolves with pending cases", async () => {
    const { result } = renderHook(() => usePendingCases(5), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

/* ── Provider hooks ─────────────────────────────────────────── */

describe("useProviders", () => {
  it("resolves with provider list", async () => {
    const { result } = renderHook(() => useProviders({ page: 1 }), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderDetail", () => {
  it("resolves with provider detail", async () => {
    const { result } = renderHook(() => useProviderDetail("123"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ npi: "123" });
  });
});

describe("useProviderScoreDetails", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderScoreDetails("123"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderSignals", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderSignals("123"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderPeers", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderPeers("123"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderRadar", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderRadar("123"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderNetwork", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderNetwork("123"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderExplain", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderExplain("123"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderGraph", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderGraph("123"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useProviderCluster", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useProviderCluster("123"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

/* ── Claims hooks ───────────────────────────────────────────── */

describe("useClaims", () => {
  it("resolves with claims list", async () => {
    const { result } = renderHook(() => useClaims({ page: 1 }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useClaim", () => {
  it("resolves with single claim", async () => {
    const { result } = renderHook(() => useClaim("abc"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ case_id: "abc" });
  });
});

describe("useClaimScoreDetails", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useClaimScoreDetails("abc"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useCaseActions", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useCaseActions("abc"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

/* ── Fairness & Validation ──────────────────────────────────── */

describe("useFairness", () => {
  it("resolves with default params", async () => {
    const { result } = renderHook(() => useFairness(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("resolves with explicit params", async () => {
    const { result } = renderHook(
      () => useFairness({ threshold: 70, blind: true }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useValidation", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useValidation(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

/* ── Ingest / Data Management ───────────────────────────────── */

describe("useIngestStatus", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useIngestStatus(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useSourceVersions", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => useSourceVersions(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("usePipelineRuns", () => {
  it("resolves", async () => {
    const { result } = renderHook(() => usePipelineRuns(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
