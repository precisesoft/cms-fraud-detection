import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { CaseDetailShell } from "../CaseDetailShell";
import {
  getClaim,
  getCaseActions,
  caseAction,
  getClaimScoreDetails,
} from "../../lib/api";
import type { Claim } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  getClaim: vi.fn(),
  getCaseActions: vi.fn(),
  caseAction: vi.fn(),
  getClaimScoreDetails: vi.fn(),
  chat: vi.fn(),
}));

const mockClaim: Claim = {
  case_id: "CASE-001",
  npi: "1111111111",
  hcpcs_cd: "99213",
  hcpcs_desc: "Office visit",
  provider_type: "Internal Medicine",
  provider_last_org_name: "Acme Clinic",
  provider_first_name: null,
  provider_state: "FL",
  state: "FL",
  place_of_service: "Office",
  tot_srvcs: 150,
  tot_benes: 80,
  avg_submitted_charge: 200,
  avg_medicare_payment_amt: 100,
  seed_risk_score: 72,
  seed_case_label: "high_risk",
  service_volume_peer_z: 2.5,
  charge_peer_z: 1.8,
  bene_peer_z: 0.5,
  services_per_bene_peer_z: 1.2,
};

const mockActionsResponse = {
  case_id: "CASE-001",
  actions: [] as never[],
  current_status: null,
};

const mockScoreDetails = {
  case_id: "CASE-001",
  npi: "1111111111",
  explainable_risk_score: 72,
  explainable_risk_band: "high_risk" as const,
  anomaly_score: 0.85,
  ml_predicted_probability: 0.65,
  hybrid_composite_score: 68,
  hybrid_risk_label: "high" as const,
  model_name: "isolation_forest_v2",
  model_version: "1.0",
};

const defaultProps = {
  backPath: "/claims",
  backLabel: "Back to Claims",
  entityType: "claim" as const,
  notFoundLabel: "Claim not found.",
  chatButtonLabel: "Ask about this claim",
  renderHeader: (data: Claim, caseId: string) => (
    <div>
      <h1>Case {caseId}</h1>
      <span>{data.seed_case_label}</span>
    </div>
  ),
  renderDetails: (data: Claim) => (
    <div>
      <h3>Details</h3>
      <span>HCPCS: {data.hcpcs_cd}</span>
    </div>
  ),
};

function renderShell(caseId = "CASE-001") {
  return render(
    <MemoryRouter initialEntries={[`/claims/${caseId}`]}>
      <Routes>
        <Route
          path="/claims/:caseId"
          element={<CaseDetailShell {...defaultProps} />}
        />
        <Route
          path="/claims"
          element={<div data-testid="claims-list">Claims List</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CaseDetailShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getClaim).mockResolvedValue(mockClaim);
    vi.mocked(getCaseActions).mockResolvedValue(mockActionsResponse);
    vi.mocked(getClaimScoreDetails).mockResolvedValue(mockScoreDetails);
    vi.mocked(caseAction).mockResolvedValue(undefined);
  });

  it("shows loading state then renders content", async () => {
    renderShell();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Case CASE-001")).toBeInTheDocument();
    });
  });

  it("shows not-found message when API returns null", async () => {
    vi.mocked(getClaim).mockResolvedValue(null as unknown as Claim);
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("Claim not found.")).toBeInTheDocument();
    });
  });

  it("renders back link with correct text", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("Case CASE-001")).toBeInTheDocument();
    });
    expect(screen.getByText(/Back to Claims/)).toBeInTheDocument();
  });

  it("renders score cards with data from API", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("Explainable Risk")).toBeInTheDocument();
    });
    expect(screen.getByText("Claim Anomaly")).toBeInTheDocument();
    expect(screen.getByText("ML Suspicion")).toBeInTheDocument();
    expect(screen.getByText("Hybrid Composite")).toBeInTheDocument();
  });

  it("renders custom details from renderDetails prop", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("HCPCS: 99213")).toBeInTheDocument();
    });
  });

  it("renders extra sections when provided", async () => {
    const propsWithExtra = {
      ...defaultProps,
      extraSections: (_data: Claim) => <div>Z-Score Panel</div>,
    };
    render(
      <MemoryRouter initialEntries={["/claims/CASE-001"]}>
        <Routes>
          <Route
            path="/claims/:caseId"
            element={<CaseDetailShell {...propsWithExtra} />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Z-Score Panel")).toBeInTheDocument();
    });
  });

  it("renders action buttons", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("Take Action")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Approve/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Flag/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Deny/ })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Escalate/ }),
    ).toBeInTheDocument();
  });

  it("calls caseAction when action button is clicked", async () => {
    vi.mocked(getCaseActions).mockResolvedValue(mockActionsResponse);
    const user = userEvent.setup();
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("Take Action")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /Approve/ }));
    await waitFor(() => {
      expect(caseAction).toHaveBeenCalledWith(
        "CASE-001",
        "APPROVED",
        "Analyst action: approve",
      );
    });
  });

  it("renders empty timeline when no actions", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("Action History")).toBeInTheDocument();
    });
    expect(screen.getByText("No actions yet.")).toBeInTheDocument();
  });

  it("shows chat button with correct label", async () => {
    renderShell();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Ask about this claim/ }),
      ).toBeInTheDocument();
    });
  });

  it("renders risk score from claim data", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("Risk Score")).toBeInTheDocument();
    });
    expect(screen.getAllByText("72").length).toBeGreaterThanOrEqual(1);
  });

  it("renders header from renderHeader prop", async () => {
    renderShell();
    await waitFor(() => {
      expect(screen.getByText("high_risk")).toBeInTheDocument();
    });
  });
});
