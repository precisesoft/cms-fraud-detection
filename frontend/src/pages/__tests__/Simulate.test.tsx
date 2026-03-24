import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Simulate } from "../Simulate";
import { simulateClaim } from "../../lib/api";

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
  simulateClaim: vi.fn(),
}));

const mockResult = {
  npi: "1234567890",
  hcpcs_cd: "99213",
  risk_score: 72,
  risk_band: "high_risk" as const,
  recommendation: "deny" as const,
  signals: [
    {
      name: "High Volume",
      category: "volume",
      direction: "risk",
      value: 150,
      threshold: 100,
      description: "Service volume exceeds peer average",
    },
  ],
  peer_comparisons: [
    {
      metric: "Total Services",
      provider_value: 150,
      peer_mean: 80,
      z_score: 3.5,
      percentile: 99,
      peer_count: 100,
    },
  ],
  provider_name: "Test Provider",
  provider_type: "Internal Medicine",
  state: "FL",
  narrative: "This provider shows anomalous billing patterns.",
  anomaly_score: 0.85,
};

function renderSimulate() {
  return render(
    <MemoryRouter>
      <Simulate />
    </MemoryRouter>,
  );
}

describe("Simulate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(simulateClaim).mockResolvedValue(mockResult);
  });

  it('renders "Claim Simulation" heading and form fields', () => {
    renderSimulate();
    expect(screen.getByText("Claim Simulation")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("1234567890")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("99213")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Run Simulation/i }),
    ).toBeInTheDocument();
  });

  it('shows "Ready to Simulate" placeholder before submission', () => {
    renderSimulate();
    expect(screen.getByText("Ready to Simulate")).toBeInTheDocument();
  });

  it("NPI and HCPCS Code inputs are required", () => {
    renderSimulate();
    const npiInput = screen.getByPlaceholderText("1234567890");
    const hcpcsInput = screen.getByPlaceholderText("99213");
    expect(npiInput).toBeRequired();
    expect(hcpcsInput).toBeRequired();
  });

  it("submitting form calls simulateClaim with form values", async () => {
    const user = userEvent.setup();
    renderSimulate();

    const npiInput = screen.getByPlaceholderText("1234567890");
    const hcpcsInput = screen.getByPlaceholderText("99213");

    await user.clear(npiInput);
    await user.type(npiInput, "1234567890");
    await user.clear(hcpcsInput);
    await user.type(hcpcsInput, "99213");

    await user.click(screen.getByRole("button", { name: /Run Simulation/i }));

    await waitFor(() => {
      expect(simulateClaim).toHaveBeenCalledOnce();
    });

    const callArg = vi.mocked(simulateClaim).mock.calls[0][0];
    expect(callArg.npi).toBe("1234567890");
    expect(callArg.hcpcs_cd).toBe("99213");
  });

  it("displays risk score and risk band after successful simulation", async () => {
    const user = userEvent.setup();
    renderSimulate();

    await user.type(screen.getByPlaceholderText("1234567890"), "1234567890");
    await user.type(screen.getByPlaceholderText("99213"), "99213");
    await user.click(screen.getByRole("button", { name: /Run Simulation/i }));

    await waitFor(() => {
      expect(screen.getByText("72")).toBeInTheDocument();
    });
    // riskBandLabel('high_risk') = 'High Risk'
    expect(screen.getByText("High Risk")).toBeInTheDocument();
  });

  it("shows error message when simulation fails", async () => {
    vi.mocked(simulateClaim).mockRejectedValue(
      new Error("Simulation service unavailable"),
    );
    const user = userEvent.setup();
    renderSimulate();

    await user.type(screen.getByPlaceholderText("1234567890"), "1234567890");
    await user.type(screen.getByPlaceholderText("99213"), "99213");
    await user.click(screen.getByRole("button", { name: /Run Simulation/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Simulation service unavailable"),
      ).toBeInTheDocument();
    });
  });

  it("displays narrative and signal after successful simulation", async () => {
    const user = userEvent.setup();
    renderSimulate();

    await user.type(screen.getByPlaceholderText("1234567890"), "1234567890");
    await user.type(screen.getByPlaceholderText("99213"), "99213");
    await user.click(screen.getByRole("button", { name: /Run Simulation/i }));

    await waitFor(() => {
      expect(
        screen.getByText("This provider shows anomalous billing patterns."),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("High Volume")).toBeInTheDocument();
  });

  it("displays recommendation after successful simulation", async () => {
    const user = userEvent.setup();
    renderSimulate();

    await user.type(screen.getByPlaceholderText("1234567890"), "1234567890");
    await user.type(screen.getByPlaceholderText("99213"), "99213");
    await user.click(screen.getByRole("button", { name: /Run Simulation/i }));

    await waitFor(() => {
      expect(screen.getByText("deny")).toBeInTheDocument();
    });
  });
});
