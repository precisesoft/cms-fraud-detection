import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Providers } from "../Providers";
import { getProviders } from "../../lib/api";

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
  getProviders: vi.fn(),
}));

const mockProviderList = {
  data: [
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
    {
      npi: "2222222222",
      provider_name: "Beta Health",
      provider_type: "Cardiology",
      state: "TX",
      city: "Houston",
      entity_code: null,
      max_seed_risk_score: 30,
      risk_band: "stable" as const,
      total_estimated_payment: 250000,
      service_line_count: null,
      revoked_2026: null,
    },
  ],
  meta: { total: 2, page: 1, per_page: 50, pages: 1 },
};

function renderProviders(initialPath = "/providers") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Providers />
    </MemoryRouter>,
  );
}

describe("Providers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProviders).mockResolvedValue(mockProviderList);
  });

  it('renders "Providers" heading', () => {
    renderProviders();
    expect(screen.getByText("Providers")).toBeInTheDocument();
  });

  it("renders provider table with names from mock data", async () => {
    renderProviders();
    await waitFor(() => {
      expect(screen.getByText("Acme Clinic")).toBeInTheDocument();
    });
    expect(screen.getByText("Beta Health")).toBeInTheDocument();
  });

  it("shows Total Results count from meta", async () => {
    renderProviders();
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });
  });

  it("search input exists with correct placeholder", () => {
    renderProviders();
    expect(
      screen.getByPlaceholderText("Search by name, NPI..."),
    ).toBeInTheDocument();
  });

  it("risk band select has All/High Risk/Review/Stable options", () => {
    renderProviders();
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "All Risk Bands" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "High Risk" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Review" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Stable" })).toBeInTheDocument();
  });

  it('pagination shows "Page 1 of 1" text', async () => {
    renderProviders();
    await waitFor(() => {
      expect(screen.getByText(/Page 1 of 1/)).toBeInTheDocument();
    });
  });

  it("renders table column headers", () => {
    renderProviders();
    expect(screen.getByText("Provider")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
  });

  it("renders Previous and Next pagination buttons", () => {
    renderProviders();
    expect(
      screen.getByRole("button", { name: "Previous" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeInTheDocument();
  });

  it("clears providers on API error", async () => {
    vi.mocked(getProviders).mockRejectedValue(new Error("Network error"));
    renderProviders();
    await waitFor(() => {
      expect(getProviders).toHaveBeenCalled();
    });
    // After error, table body should have no provider rows
    expect(screen.queryByText("Acme Clinic")).not.toBeInTheDocument();
  });

  it("typing in search input updates the search term", async () => {
    const user = userEvent.setup();
    renderProviders();
    const input = screen.getByPlaceholderText("Search by name, NPI...");
    await user.type(input, "cardio");
    expect(input).toHaveValue("cardio");
  });

  it("typing in state filter uppercases and limits to 2 chars", async () => {
    const user = userEvent.setup();
    renderProviders();
    const input = screen.getByPlaceholderText("State (e.g. FL)");
    await user.type(input, "flo");
    // .toUpperCase().slice(0, 2) means "flo" -> each keystroke uppercased and sliced
    expect(input).toHaveValue("FL");
  });

  it("changing risk band select triggers re-fetch", async () => {
    const user = userEvent.setup();
    renderProviders();
    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "high_risk");
    expect(select).toHaveValue("high_risk");
    // Effect runs with the new filter
    await waitFor(() => {
      const lastCall = vi.mocked(getProviders).mock.calls.at(-1)?.[0];
      expect(lastCall?.risk_band).toBe("high_risk");
    });
  });

  it("Previous button is disabled on page 1", () => {
    renderProviders();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
  });

  it("Next button is disabled when page equals pages", async () => {
    renderProviders();
    await waitFor(() => {
      expect(screen.getByText("Acme Clinic")).toBeInTheDocument();
    });
    // meta.pages = 1, meta.page = 1, so Next is disabled
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("clicking Next advances page when multiple pages exist", async () => {
    vi.mocked(getProviders).mockResolvedValue({
      data: mockProviderList.data,
      meta: { total: 100, page: 1, per_page: 50, pages: 2 },
    });
    const user = userEvent.setup();
    renderProviders();
    await waitFor(() => {
      expect(screen.getByText("Acme Clinic")).toBeInTheDocument();
    });
    const callsBefore = vi.mocked(getProviders).mock.calls.length;
    const nextBtn = screen.getByRole("button", { name: "Next" });
    expect(nextBtn).not.toBeDisabled();
    await user.click(nextBtn);
    // Verify getProviders was called with page=2 at some point after click
    await waitFor(() => {
      const calls = vi.mocked(getProviders).mock.calls.slice(callsBefore);
      expect(calls.some((c) => c[0]?.page === 2)).toBe(true);
    });
  });

  it("reads initial state from URL search params", () => {
    renderProviders("/providers?state=TX&risk_band=high_risk");
    const stateInput = screen.getByPlaceholderText("State (e.g. FL)");
    expect(stateInput).toHaveValue("TX");
    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("high_risk");
  });

  it("renders fallback dashes when provider fields are null", async () => {
    vi.mocked(getProviders).mockResolvedValue({
      data: [
        {
          npi: "3333333333",
          provider_name: "Null Fields Corp",
          provider_type: null,
          state: null,
          city: null,
          entity_code: null,
          max_seed_risk_score: null,
          risk_band: "stable" as const,
          total_estimated_payment: 0,
          service_line_count: null,
          revoked_2026: null,
        },
      ],
      meta: { total: 1, page: 1, per_page: 50, pages: 1 },
    });
    renderProviders();
    await waitFor(() => {
      expect(screen.getByText("Null Fields Corp")).toBeInTheDocument();
    });
    // provider_type ?? '—' and max_seed_risk_score ?? '—' render standalone
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
    // city ?? '—', state ?? '—' render as "—, —" in a single node
    expect(screen.getByText("—, —")).toBeInTheDocument();
  });

  it("does not update state after unmount (success path)", async () => {
    let resolveApi!: (v: typeof mockProviderList) => void;
    vi.mocked(getProviders).mockReturnValue(
      new Promise((r) => {
        resolveApi = r;
      }),
    );
    const { unmount } = renderProviders();
    unmount();
    resolveApi(mockProviderList);
    await new Promise((r) => setTimeout(r, 0));
  });

  it("does not update state after unmount (error path)", async () => {
    let rejectApi!: (e: Error) => void;
    vi.mocked(getProviders).mockReturnValue(
      new Promise((_, r) => {
        rejectApi = r;
      }),
    );
    const { unmount } = renderProviders();
    unmount();
    rejectApi(new Error("stale"));
    await new Promise((r) => setTimeout(r, 0));
  });

  it("clicking Previous goes back a page when page > 1", async () => {
    vi.mocked(getProviders).mockResolvedValue({
      data: mockProviderList.data,
      meta: { total: 100, page: 2, per_page: 50, pages: 2 },
    });
    const user = userEvent.setup();
    renderProviders();
    await waitFor(() => {
      expect(screen.getByText("Acme Clinic")).toBeInTheDocument();
    });
    const prevBtn = screen.getByRole("button", { name: "Previous" });
    expect(prevBtn).not.toBeDisabled();
    const callsBefore = vi.mocked(getProviders).mock.calls.length;
    await user.click(prevBtn);
    await waitFor(() => {
      const calls = vi.mocked(getProviders).mock.calls.slice(callsBefore);
      expect(calls.some((c) => c[0]?.page === 1)).toBe(true);
    });
  });
});
