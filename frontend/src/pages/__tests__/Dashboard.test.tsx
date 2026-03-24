import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "../Dashboard";
import { getDashboard, getPendingCases } from "../../lib/api";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

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
    mockNavigate.mockReset();
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

  it("clicking a KPI card navigates to its href", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Total Providers")).toBeInTheDocument();
    });
    const card = screen.getByText("Total Providers").closest("button")!;
    await user.click(card);
    expect(mockNavigate).toHaveBeenCalledWith("/providers");
  });

  it("clicking High Risk KPI navigates with risk_band param", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("1,234")).toBeInTheDocument();
    });
    // Find High Risk KPI button by its label
    const allHighRisk = screen.getAllByText("High Risk");
    const kpiCard = allHighRisk
      .find((el) => el.closest("button"))
      ?.closest("button");
    expect(kpiCard).toBeTruthy();
    await user.click(kpiCard!);
    expect(mockNavigate).toHaveBeenCalledWith("/providers?risk_band=high_risk");
  });

  it("shows empty state when no pending cases", async () => {
    vi.mocked(getPendingCases).mockResolvedValue([]);
    renderDashboard();
    await waitFor(() => {
      expect(
        screen.getByText("No cases are currently pending review."),
      ).toBeInTheDocument();
    });
  });

  it("renders risk distribution percentages", async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Risk Distribution")).toBeInTheDocument();
    });
    // 50/(50+200+984) = 4.1%, 200/1234 = 16.2%, 984/1234 = 79.7%
    expect(screen.getByText("4.1%")).toBeInTheDocument();
  });

  it("shows fallback text when provider fields are null", async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      ...mockStats,
      top_providers: [
        {
          npi: "9999999999",
          provider_name: "Null Fields Provider",
          provider_type: null,
          state: null,
          city: null,
          entity_code: null,
          max_seed_risk_score: null,
          risk_band: "review" as const,
          total_estimated_payment: 100,
          service_line_count: null,
          revoked_2026: null,
        },
      ],
    });
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Null Fields Provider")).toBeInTheDocument();
    });
    expect(screen.getByText(/Unknown/)).toBeInTheDocument();
  });

  it("shows 0% when risk distribution totals zero", async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      ...mockStats,
      risk_distribution: { high_risk: 0, review: 0, stable: 0 },
    });
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Risk Distribution")).toBeInTheDocument();
    });
    const zeros = screen.getAllByText("0%");
    expect(zeros.length).toBe(3);
  });

  it("shows fallback text when pending case fields are null", async () => {
    vi.mocked(getPendingCases).mockResolvedValue([
      {
        case_id: "NULL001",
        npi: "8888888888",
        provider_last_org_name: null,
        hcpcs_cd: "99213",
        hcpcs_desc: null,
        seed_risk_score: null,
        seed_case_label: null,
        avg_submitted_charge: 200,
        tot_srvcs: null,
      },
    ]);
    renderDashboard();
    await waitFor(() => {
      // Falls back to npi when provider_last_org_name is null
      expect(screen.getByText("8888888888")).toBeInTheDocument();
    });
  });
});
