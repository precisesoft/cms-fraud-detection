import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "../Dashboard";
import { getDashboard, getPendingCases } from "../../lib/api";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      username: "analyst",
      role: "analyst",
      full_name: "Test Analyst",
    },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("../../lib/api", () => ({
  getDashboard: vi.fn(),
  getPendingCases: vi.fn(),
}));

const mockStats = {
  total_providers: 1234,
  total_cases: 5678,
  risk_distribution: { high_risk: 50, review: 200, stable: 984 },
  top_providers: [
    {
      npi: "1111111111",
      provider_name: "Acme Clinic",
      provider_type: "Internal Medicine",
      state: "FL",
      city: "Miami",
      entity_code: null,
      max_seed_risk_score: 85,
      risk_band: "high_risk" as const,
      total_estimated_payment: 500000,
      service_line_count: null,
      revoked_2026: null,
    },
  ],
};

const mockPending = [
  {
    case_id: "CASE001",
    npi: "2222222222",
    provider_last_org_name: "Beta Labs",
    hcpcs_cd: "99213",
    hcpcs_desc: "Office Visit",
    seed_risk_score: 72,
    seed_case_label: null,
    avg_submitted_charge: 150,
    tot_srvcs: null,
  },
];

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getDashboard).mockResolvedValue(mockStats);
    vi.mocked(getPendingCases).mockResolvedValue(mockPending);
  });

  it('renders "Dashboard" heading', () => {
    renderDashboard();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders KPI cards with correct values after API resolves", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("1,234")).toBeInTheDocument();
    });
    expect(screen.getByText("5,678")).toBeInTheDocument();
    // "50" appears in both KPI card and Risk Distribution
    expect(screen.getAllByText("50").length).toBeGreaterThanOrEqual(1);
    // Pending Review count equals pending.length = 1
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("renders all four KPI card labels", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Total Providers")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Cases")).toBeInTheDocument();
    // "High Risk" appears in both KPI card and Risk Distribution — verify at least one
    expect(screen.getAllByText("High Risk").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Pending Review")).toBeInTheDocument();
  });

  it("shows Top Flagged Providers section with provider name", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Top Flagged Providers")).toBeInTheDocument();
    });
    expect(screen.getByText("Acme Clinic")).toBeInTheDocument();
  });

  it("shows Pending Review Cases section with case data", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Pending Review Cases")).toBeInTheDocument();
    });
    expect(screen.getByText("Beta Labs")).toBeInTheDocument();
  });

  it("shows error message when getDashboard rejects", async () => {
    vi.mocked(getDashboard).mockRejectedValue(
      new Error("Failed to load dashboard"),
    );
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Failed to load dashboard")).toBeInTheDocument();
    });
  });

  it("renders Risk Distribution section with band labels", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Risk Distribution")).toBeInTheDocument();
    });
    // "Review" and "Stable" may also appear in multiple sections
    expect(screen.getAllByText("Review").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Stable").length).toBeGreaterThanOrEqual(1);
  });
});
