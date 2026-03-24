import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getToken,
  setToken,
  clearToken,
  getHealth,
  getDashboard,
  getProviders,
  getClaims,
  scoreClaim,
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
    expect(url).toMatch(/\/api\/score$/);
  });
});
