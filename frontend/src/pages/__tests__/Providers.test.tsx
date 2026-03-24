import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
});
