import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getToken,
  setToken,
  clearToken,
  getHealth,
  getDashboard,
  getHeatmap,
  getProviders,
  getProviderDetail,
  getProviderScoreDetails,
  getProviderSignals,
  getProviderPeers,
  getProviderRadar,
  getProviderNetwork,
  getProviderGraph,
  getClaims,
  getClaim,
  getClaimScoreDetails,
  simulateClaim,
  scoreClaim,
  getFairness,
  chat,
  caseAction,
  getCaseActions,
  getPendingCases,
  getValidation,
  login,
  getMe,
} from "../api";

/* ── localStorage mock ─────────────────────────────────────── */

const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

vi.stubGlobal("localStorage", localStorageMock);

/* ── fetch mock ────────────────────────────────────────────── */

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

/* ── window.location mock ──────────────────────────────────── */

const locationMock = { href: "" };
Object.defineProperty(globalThis, "location", {
  value: locationMock,
  writable: true,
});

/* ── helpers ───────────────────────────────────────────────── */

function okResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response);
}

function errorResponse(status: number, text = "") {
  return Promise.resolve({
    ok: false,
    status,
    json: () => Promise.resolve(null),
    text: () => Promise.resolve(text),
  } as Response);
}

/* ── reset between tests ───────────────────────────────────── */

beforeEach(() => {
  vi.clearAllMocks();
  locationMock.href = "";
  localStorageMock.getItem.mockReturnValue(null);
});

afterEach(() => {
  vi.restoreAllMocks();
});

/* ── Token management ──────────────────────────────────────── */

describe("getToken", () => {
  it("returns null when no token stored", () => {
    localStorageMock.getItem.mockReturnValue(null);
    expect(getToken()).toBeNull();
    expect(localStorageMock.getItem).toHaveBeenCalledWith("argus_token");
  });

  it("returns the stored token string", () => {
    localStorageMock.getItem.mockReturnValue("tok_abc123");
    expect(getToken()).toBe("tok_abc123");
  });
});

describe("setToken", () => {
  it("writes the token under argus_token key", () => {
    setToken("my_token");
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "argus_token",
      "my_token",
    );
  });
});

describe("clearToken", () => {
  it("removes argus_token from localStorage", () => {
    clearToken();
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("argus_token");
  });
});

/* ── Auth header attachment ────────────────────────────────── */

describe("getHealth — auth header", () => {
  it("attaches Bearer token when one is stored", async () => {
    localStorageMock.getItem.mockReturnValue("valid_token");
    fetchMock.mockReturnValue(okResponse({ status: "ok" }));

    await getHealth();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["Authorization"]).toBe(
      "Bearer valid_token",
    );
  });

  it("omits Authorization header when no token is stored", async () => {
    localStorageMock.getItem.mockReturnValue(null);
    fetchMock.mockReturnValue(okResponse({ status: "ok" }));

    await getHealth();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(
      (init.headers as Record<string, string>)["Authorization"],
    ).toBeUndefined();
  });

  it("calls /health endpoint", async () => {
    fetchMock.mockReturnValue(okResponse({ status: "ok" }));

    await getHealth();

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/health$/);
  });
});

/* ── 401 redirect behavior ─────────────────────────────────── */

describe("401 handling", () => {
  it("clears token and redirects to /login on 401", async () => {
    localStorageMock.getItem.mockReturnValue("expired_token");
    fetchMock.mockReturnValue(errorResponse(401));

    await expect(getDashboard()).rejects.toThrow("Session expired");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("argus_token");
    expect(locationMock.href).toBe("/login");
  });
});

/* ── Non-ok error propagation ──────────────────────────────── */

describe("non-ok error handling", () => {
  it("throws with response body text when available", async () => {
    fetchMock.mockReturnValue(errorResponse(422, "Unprocessable entity"));

    await expect(getHealth()).rejects.toThrow("Unprocessable entity");
  });

  it("throws with status code message when body is empty", async () => {
    fetchMock.mockReturnValue(errorResponse(500, ""));

    await expect(getHealth()).rejects.toThrow("Request failed: 500");
  });
});

/* ── getProviders query params ─────────────────────────────── */

describe("getProviders — query params", () => {
  beforeEach(() => {
    fetchMock.mockReturnValue(
      okResponse({
        data: [],
        meta: { total: 0, page: 1, per_page: 20, pages: 0 },
      }),
    );
  });

  it("calls /api/providers with no suffix when no params given", async () => {
    await getProviders();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/providers$/);
  });

  it("appends page and per_page params", async () => {
    await getProviders({ page: 2, per_page: 10 });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("page=2");
    expect(url).toContain("per_page=10");
  });

  it("appends state filter", async () => {
    await getProviders({ state: "TX" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("state=TX");
  });

  it("appends risk_band filter", async () => {
    await getProviders({ risk_band: "high_risk" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("risk_band=high_risk");
  });

  it("appends q search term", async () => {
    await getProviders({ q: "cardio" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("q=cardio");
  });

  it("appends provider_type filter", async () => {
    await getProviders({ provider_type: "1" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("provider_type=1");
  });

  it("combines multiple filters", async () => {
    await getProviders({ state: "CA", risk_band: "review", page: 3 });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("state=CA");
    expect(url).toContain("risk_band=review");
    expect(url).toContain("page=3");
  });
});

/* ── getClaims query params ────────────────────────────────── */

describe("getClaims — query params", () => {
  beforeEach(() => {
    fetchMock.mockReturnValue(
      okResponse({
        data: [],
        meta: { total: 0, page: 1, per_page: 20, pages: 0 },
      }),
    );
  });

  it("calls /api/claims with no suffix when no params given", async () => {
    await getClaims();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/claims$/);
  });

  it("appends npi filter", async () => {
    await getClaims({ npi: "1234567890" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("npi=1234567890");
  });

  it("appends case_label filter", async () => {
    await getClaims({ case_label: "high_risk" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("case_label=high_risk");
  });

  it("appends risk_min and risk_max", async () => {
    await getClaims({ risk_min: 0, risk_max: 30 });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("risk_min=0");
    expect(url).toContain("risk_max=30");
  });

  it("includes risk_min=0 (falsy value must not be dropped)", async () => {
    await getClaims({ risk_min: 0 });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("risk_min=0");
  });

  it("appends state filter", async () => {
    await getClaims({ state: "FL" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("state=FL");
  });

  it("appends provider_type filter", async () => {
    await getClaims({ provider_type: "Cardiology" });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("provider_type=Cardiology");
  });

  it("appends page param", async () => {
    await getClaims({ page: 3 });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("page=3");
  });

  it("appends per_page param", async () => {
    await getClaims({ per_page: 25 });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("per_page=25");
  });
});

/* ── scoreClaim POST body ──────────────────────────────────── */

describe("scoreClaim — POST body", () => {
  it("sends payload as JSON in request body", async () => {
    const scorePayload = {
      npi: "9999999999",
      hcpcs_cd: "99213",
      tot_srvcs: 100,
      avg_submitted_charge: 250,
    };

    fetchMock.mockReturnValue(
      okResponse({
        npi: "9999999999",
        risk_score: 72,
        legitimacy_score: 28,
        risk_band: "high_risk",
        signals: [],
        narrative: null,
        anomaly_score: null,
      }),
    );

    await scoreClaim(scorePayload);

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual(scorePayload);
  });

  it("calls /api/score endpoint", async () => {
    fetchMock.mockReturnValue(
      okResponse({
        npi: "1",
        risk_score: 10,
        legitimacy_score: 90,
        risk_band: "stable",
        signals: [],
        narrative: null,
        anomaly_score: null,
      }),
    );

    await scoreClaim({ npi: "1" });

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/v2\/score$/);
  });
});

/* ── getHeatmap ────────────────────────────────────────────── */

describe("getHeatmap", () => {
  it("calls /api/dashboard/heatmap", async () => {
    fetchMock.mockReturnValue(okResponse({ data: [] }));
    await getHeatmap();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/dashboard\/heatmap$/);
  });
});

/* ── getProviderDetail ─────────────────────────────────────── */

describe("getProviderDetail", () => {
  it("calls /api/providers/:npi", async () => {
    fetchMock.mockReturnValue(okResponse({ npi: "123" }));
    await getProviderDetail("123");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/providers\/123$/);
  });
});

/* ── getProviderScoreDetails ──────────────────────────────── */

describe("getProviderScoreDetails", () => {
  it("calls /api/providers/:npi/score-details", async () => {
    fetchMock.mockReturnValue(okResponse({ npi: "123" }));
    await getProviderScoreDetails("123");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/providers\/123\/score-details$/);
  });
});

/* ── getProviderSignals ────────────────────────────────────── */

describe("getProviderSignals", () => {
  it("calls /api/providers/:npi/signals", async () => {
    fetchMock.mockReturnValue(okResponse([]));
    await getProviderSignals("456");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/providers\/456\/signals$/);
  });
});

/* ── getProviderPeers ──────────────────────────────────────── */

describe("getProviderPeers", () => {
  it("calls /api/providers/:npi/peers", async () => {
    fetchMock.mockReturnValue(
      okResponse({ npi: "789", lines: [], total_lines: 0 }),
    );
    await getProviderPeers("789");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/providers\/789\/peers$/);
  });
});

/* ── getProviderRadar ──────────────────────────────────────── */

describe("getProviderRadar", () => {
  it("calls /api/providers/:npi/radar", async () => {
    fetchMock.mockReturnValue(okResponse({ npi: "111", dimensions: [] }));
    await getProviderRadar("111");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/providers\/111\/radar$/);
  });
});

/* ── getProviderNetwork ────────────────────────────────────── */

describe("getProviderNetwork", () => {
  it("calls /api/network/:npi", async () => {
    fetchMock.mockReturnValue(
      okResponse({
        npi: "222",
        zip5: null,
        same_zip_flagged: [],
        same_org_flagged: [],
        zip_risk_summary: null,
      }),
    );
    await getProviderNetwork("222");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/network\/222$/);
  });
});

/* ── getProviderGraph ──────────────────────────────────────── */

describe("getProviderGraph", () => {
  it("calls /api/graph/:npi", async () => {
    fetchMock.mockReturnValue(okResponse({ npi: "333", nodes: [], edges: [] }));
    await getProviderGraph("333");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/graph\/333$/);
  });
});

/* ── getClaim ──────────────────────────────────────────────── */

describe("getClaim", () => {
  it("calls /api/claims/:caseId with URL encoding", async () => {
    fetchMock.mockReturnValue(okResponse({ case_id: "C-001", npi: "1" }));
    await getClaim("C-001");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/claims\/C-001$/);
  });
});

/* ── getClaimScoreDetails ─────────────────────────────────── */

describe("getClaimScoreDetails", () => {
  it("calls /api/claims/:caseId/score-details with URL encoding", async () => {
    fetchMock.mockReturnValue(okResponse({ case_id: "C-001", npi: "1" }));
    await getClaimScoreDetails("C-001");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/claims\/C-001\/score-details$/);
  });
});

/* ── simulateClaim ─────────────────────────────────────────── */

describe("simulateClaim", () => {
  it("sends POST to /api/v2/claims/simulate with payload", async () => {
    const payload = {
      npi: "111",
      hcpcs_cd: "99213",
      submitted_charge: 100,
      num_services: 10,
      num_benes: 5,
    };
    fetchMock.mockReturnValue(
      okResponse({
        npi: "111",
        hcpcs_cd: "99213",
        risk_score: 50,
        risk_band: "review",
        recommendation: "review",
        signals: [],
        peer_comparisons: [],
        provider_name: null,
        provider_type: null,
        state: null,
        narrative: null,
        anomaly_score: null,
        ml_predicted_probability: null,
      }),
    );
    await simulateClaim(payload);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v2\/claims\/simulate$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual(payload);
  });
});

/* ── getFairness ───────────────────────────────────────────── */

describe("getFairness", () => {
  it("calls /api/fairness with no params", async () => {
    fetchMock.mockReturnValue(okResponse({ by_state: [], by_specialty: [] }));
    await getFairness();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/fairness$/);
  });

  it("appends threshold and blind params", async () => {
    fetchMock.mockReturnValue(okResponse({ by_state: [], by_specialty: [] }));
    await getFairness({ threshold: 50, blind: true });
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("threshold=50");
    expect(url).toContain("blind=true");
  });
});

/* ── chat ──────────────────────────────────────────────────── */

describe("chat", () => {
  it("sends POST to /api/chat with message and history", async () => {
    fetchMock.mockReturnValue(
      okResponse({
        answer: "hello",
        sql: null,
        columns: [],
        rows: [],
        row_count: 0,
        duration_ms: 10,
        chart_spec: null,
      }),
    );
    await chat("test question", [{ role: "user", content: "prior" }]);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/chat$/);
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body.message).toBe("test question");
    expect(body.history).toHaveLength(1);
  });

  it("defaults to empty history", async () => {
    fetchMock.mockReturnValue(
      okResponse({
        answer: "ok",
        sql: null,
        columns: [],
        rows: [],
        row_count: 0,
        duration_ms: 0,
        chart_spec: null,
      }),
    );
    await chat("hi");
    const body = JSON.parse(
      (fetchMock.mock.calls[0] as [string, RequestInit])[1].body as string,
    );
    expect(body.history).toEqual([]);
  });
});

/* ── caseAction ────────────────────────────────────────────── */

describe("caseAction", () => {
  it("sends POST to /api/cases/:caseId/action", async () => {
    fetchMock.mockReturnValue(
      okResponse({ case_id: "C1", action: "APPROVED", message: "ok" }),
    );
    await caseAction("C1", "APPROVED", "looks good");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/cases\/C1\/action$/);
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body.action).toBe("APPROVED");
    expect(body.notes).toBe("looks good");
  });
});

/* ── getCaseActions ────────────────────────────────────────── */

describe("getCaseActions", () => {
  it("calls /api/cases/:caseId/actions", async () => {
    fetchMock.mockReturnValue(
      okResponse({ case_id: "C2", actions: [], current_status: null }),
    );
    await getCaseActions("C2");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/cases\/C2\/actions$/);
  });
});

/* ── getPendingCases ───────────────────────────────────────── */

describe("getPendingCases", () => {
  it("calls /api/cases/pending with default limit", async () => {
    fetchMock.mockReturnValue(okResponse({ total_count: 0, cases: [] }));
    await getPendingCases();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/api/cases/pending?limit=50");
  });

  it("respects custom limit", async () => {
    fetchMock.mockReturnValue(okResponse({ total_count: 0, cases: [] }));
    await getPendingCases(10);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("limit=10");
  });

  it("passes risk_band query parameter when provided", async () => {
    fetchMock.mockReturnValue(okResponse({ total_count: 0, cases: [] }));
    await getPendingCases(50, "high_risk");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("risk_band=high_risk");
  });
});

/* ── getValidation ─────────────────────────────────────────── */

describe("getValidation", () => {
  it("calls /api/validation", async () => {
    fetchMock.mockReturnValue(okResponse({ overall_detection_rate: 0.8 }));
    await getValidation();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/validation$/);
  });
});

/* ── login ─────────────────────────────────────────────────── */

describe("login", () => {
  it("sends POST to /api/auth/login with credentials", async () => {
    fetchMock.mockReturnValue(
      okResponse({
        access_token: "tok123",
        token_type: "bearer",
        user: { id: 1, username: "admin", role: "admin", full_name: null },
      }),
    );
    await login("admin", "pass");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/auth\/login$/);
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body.username).toBe("admin");
    expect(body.password).toBe("pass");
  });
});

/* ── getMe ─────────────────────────────────────────────────── */

describe("getMe", () => {
  it("calls /api/auth/me", async () => {
    fetchMock.mockReturnValue(
      okResponse({ id: 1, username: "admin", role: "admin", full_name: null }),
    );
    await getMe();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/auth\/me$/);
  });
});
