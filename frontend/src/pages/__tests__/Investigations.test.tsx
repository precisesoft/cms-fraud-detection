import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Investigations } from "../Investigations";
import { getPendingCases } from "../../lib/api";
import type { PendingCasesResponse } from "../../lib/api";

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
  getPendingCases: vi.fn(),
}));

const mockCases = [
  {
    case_id: "1111111111|99213",
    npi: "1111111111",
    provider_last_org_name: "Alpha Clinic",
    hcpcs_cd: "99213",
    hcpcs_desc: "Office Visit",
    seed_risk_score: 88,
    seed_case_label: "high_risk",
    avg_submitted_charge: 5000,
    tot_srvcs: 200,
  },
  {
    case_id: "2222222222|99214",
    npi: "2222222222",
    provider_last_org_name: "Beta Health",
    hcpcs_cd: "99214",
    hcpcs_desc: null,
    seed_risk_score: 45,
    seed_case_label: "review",
    avg_submitted_charge: 3000,
    tot_srvcs: 100,
  },
  {
    case_id: "3333333333|99215",
    npi: "3333333333",
    provider_last_org_name: "Gamma Medical",
    hcpcs_cd: "99215",
    hcpcs_desc: "Complex Visit",
    seed_risk_score: 20,
    seed_case_label: "stable",
    avg_submitted_charge: 1000,
    tot_srvcs: 50,
  },
];

const allCasesResp: PendingCasesResponse = {
  total_count: 3,
  cases: mockCases,
};

function renderInvestigations() {
  return render(
    <MemoryRouter>
      <Investigations />
    </MemoryRouter>,
  );
}

describe("Investigations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPendingCases).mockResolvedValue(allCasesResp);
  });

  it("renders Investigations heading", async () => {
    renderInvestigations();
    expect(screen.getByText("Investigations")).toBeInTheDocument();
    await waitFor(() => {
      expect(getPendingCases).toHaveBeenCalledWith(200, "");
    });
  });

  it("shows case cards after loading", async () => {
    renderInvestigations();
    await waitFor(() => {
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument();
    });
    expect(screen.getByText("Beta Health")).toBeInTheDocument();
    expect(screen.getByText("Gamma Medical")).toBeInTheDocument();
  });

  it("renders filter controls: risk band select, min score input, sort button", async () => {
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Min score")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Score:/i }),
    ).toBeInTheDocument();
  });

  it("risk band select has All Risk Bands / High Risk / Review / Stable options", async () => {
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    const select = screen.getByRole("combobox");
    expect(
      screen.getByRole("option", { name: "All Risk Bands" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "High Risk" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Review" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Stable" })).toBeInTheDocument();
    expect(select).toHaveValue("");
  });

  it("filtering by high_risk band re-fetches with risk_band param", async () => {
    const user = userEvent.setup();
    // First call returns all cases
    vi.mocked(getPendingCases).mockResolvedValueOnce(allCasesResp);
    // Second call (after selecting high_risk) returns only high_risk
    vi.mocked(getPendingCases).mockResolvedValueOnce({
      total_count: 1,
      cases: [mockCases[0]],
    });
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "high_risk");
    await waitFor(() => {
      expect(getPendingCases).toHaveBeenCalledWith(200, "high_risk");
    });
    await waitFor(() => {
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument();
    });
    expect(screen.queryByText("Beta Health")).not.toBeInTheDocument();
    expect(screen.queryByText("Gamma Medical")).not.toBeInTheDocument();
  });

  it("filtering by review band re-fetches with risk_band param", async () => {
    const user = userEvent.setup();
    vi.mocked(getPendingCases).mockResolvedValueOnce(allCasesResp);
    vi.mocked(getPendingCases).mockResolvedValueOnce({
      total_count: 1,
      cases: [mockCases[1]],
    });
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Beta Health")).toBeInTheDocument(),
    );
    await user.selectOptions(screen.getByRole("combobox"), "review");
    await waitFor(() => {
      expect(getPendingCases).toHaveBeenCalledWith(200, "review");
    });
    await waitFor(() => {
      expect(screen.queryByText("Alpha Clinic")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Beta Health")).toBeInTheDocument();
    expect(screen.queryByText("Gamma Medical")).not.toBeInTheDocument();
  });

  it("filtering by min score hides cases below threshold", async () => {
    const user = userEvent.setup();
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    const input = screen.getByPlaceholderText("Min score");
    await user.clear(input);
    await user.type(input, "50");
    expect(screen.getByText("Alpha Clinic")).toBeInTheDocument();
    expect(screen.queryByText("Beta Health")).not.toBeInTheDocument();
    expect(screen.queryByText("Gamma Medical")).not.toBeInTheDocument();
  });

  it("shows No Matches state when filters exclude all cases", async () => {
    const user = userEvent.setup();
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    const input = screen.getByPlaceholderText("Min score");
    await user.clear(input);
    await user.type(input, "99");
    expect(screen.getByText("No Matches")).toBeInTheDocument();
  });

  it("default sort order is highest first (desc)", async () => {
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /Highest First/i }),
    ).toBeInTheDocument();
    const cards = screen.getAllByText(/Clinic|Health|Medical/);
    expect(cards[0]).toHaveTextContent("Alpha Clinic");
  });

  it("toggling sort button switches to lowest first", async () => {
    const user = userEvent.setup();
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    const sortBtn = screen.getByRole("button", { name: /Highest First/i });
    await user.click(sortBtn);
    expect(
      screen.getByRole("button", { name: /Lowest First/i }),
    ).toBeInTheDocument();
  });

  it("shows All Clear when no cases are returned", async () => {
    vi.mocked(getPendingCases).mockResolvedValue({
      total_count: 0,
      cases: [],
    });
    renderInvestigations();
    await waitFor(() => {
      expect(screen.getByText("All Clear")).toBeInTheDocument();
    });
  });

  it("shows count badge with filtered / total when min score filter is active", async () => {
    const user = userEvent.setup();
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    const input = screen.getByPlaceholderText("Min score");
    await user.clear(input);
    await user.type(input, "50");
    // displayed=1 (only Alpha 88>=50), totalCount=3
    expect(screen.getByText(/1 of 3 cases/)).toBeInTheDocument();
  });

  it("shows full count badge when no filter is active", async () => {
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    expect(screen.getByText("3 cases pending review")).toBeInTheDocument();
  });

  it("high_risk card keeps neutral border styling", async () => {
    const { container } = renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    const links = container.querySelectorAll("a[href]");
    const highRiskLink = Array.from(links).find((el) =>
      el.textContent?.includes("Alpha Clinic"),
    );
    expect(highRiskLink?.className).toMatch(/border-slate-200/);
  });

  it("review card keeps neutral border styling", async () => {
    const { container } = renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Beta Health")).toBeInTheDocument(),
    );
    const links = container.querySelectorAll("a[href]");
    const reviewLink = Array.from(links).find((el) =>
      el.textContent?.includes("Beta Health"),
    );
    expect(reviewLink?.className).toMatch(/border-slate-200/);
  });

  it("high_risk card shows rose accent treatment", async () => {
    const { container } = renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Alpha Clinic")).toBeInTheDocument(),
    );
    expect(container.querySelector(".bg-rose-500")).toBeInTheDocument();
  });

  it("review card shows amber accent treatment", async () => {
    const { container } = renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("Beta Health")).toBeInTheDocument(),
    );
    expect(container.querySelector(".bg-amber-500")).toBeInTheDocument();
  });

  it("high_risk score renders with text-3xl class", async () => {
    renderInvestigations();
    await waitFor(() =>
      expect(screen.getByText("88")).toBeInTheDocument(),
    );
    const scoreEl = screen.getByText("88");
    expect(scoreEl.className).toMatch(/text-3xl/);
  });

  it("review score renders with text-2xl class", async () => {
    renderInvestigations();
    await waitFor(() => expect(screen.getByText("45")).toBeInTheDocument());
    const scoreEl = screen.getByText("45");
    expect(scoreEl.className).toMatch(/text-2xl/);
  });

  it("stable score renders with text-xl class", async () => {
    renderInvestigations();
    await waitFor(() => expect(screen.getByText("20")).toBeInTheDocument());
    const scoreEl = screen.getByText("20");
    expect(scoreEl.className).toMatch(/text-xl/);
  });

  it("does not update state after unmount", async () => {
    let resolve: ((v: PendingCasesResponse) => void) | undefined;
    vi.mocked(getPendingCases).mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );
    const { unmount } = renderInvestigations();
    unmount();
    resolve?.({ total_count: 3, cases: mockCases });
    await new Promise((r) => setTimeout(r, 0));
  });
});
