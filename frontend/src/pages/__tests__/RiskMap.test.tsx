import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { RiskMap } from "../RiskMap";
import { getHeatmap } from "../../lib/api";

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
  getHeatmap: vi.fn(),
}));

vi.mock("react-simple-maps", () => ({
  ComposableMap: ({ children }: { children: React.ReactNode }) => <div data-testid="map">{children}</div>,
  Geographies: ({ children }: { children: (props: { geographies: Array<{ id: string; rsmKey: string }> }) => React.ReactNode }) =>
    <div>{children({ geographies: [{ id: "12", rsmKey: "FL" }, { id: "48", rsmKey: "TX" }] })}</div>,
  Geography: ({ geography, onMouseEnter, onMouseLeave }: { geography: { id: string }; onMouseEnter?: (event: MouseEvent) => void; onMouseLeave?: () => void }) => (
    <button
      type="button"
      data-testid={`state-${geography.id}`}
      onMouseEnter={() => onMouseEnter?.({ clientX: 10, clientY: 10 } as MouseEvent)}
      onMouseLeave={onMouseLeave}
    >
      {geography.id}
    </button>
  ),
}));

const mockHeatmap = {
  data: [
    { state: "FL", provider_count: 10, avg_risk_score: 24.3, flagged_count: 2 },
    { state: "TX", provider_count: 8, avg_risk_score: 18.1, flagged_count: 1 },
  ],
};

function renderRiskMap() {
  return render(
    <MemoryRouter initialEntries={["/risk-map"]}>
      <Routes>
        <Route path="/risk-map" element={<RiskMap />} />
        <Route path="/providers" element={<div data-testid="providers-page">Providers page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RiskMap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getHeatmap).mockResolvedValue(mockHeatmap);
  });

  it("renders state rankings from heatmap data", async () => {
    renderRiskMap();

    await waitFor(() => {
      expect(screen.getByText("FL")).toBeInTheDocument();
    });
    expect(screen.getByText("TX")).toBeInTheDocument();
  });

  it("links a state row to the providers page with the state query", async () => {
    const user = userEvent.setup();
    renderRiskMap();

    const floridaLabel = await screen.findByText("FL");
    const floridaLink = floridaLabel.closest("a");
    expect(floridaLink).not.toBeNull();
    expect(floridaLink).toHaveAttribute("href", "/providers?state=FL");

    await user.click(floridaLink!);

    await waitFor(() => {
      expect(screen.getByTestId("providers-page")).toBeInTheDocument();
    });
  });
});