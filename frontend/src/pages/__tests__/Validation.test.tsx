import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Validation } from "../Validation";
import { getValidation } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  getValidation: vi.fn(),
}));

vi.mock("recharts", () => {
  const MockContainer = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-mock">{children}</div>
  );
  return {
    ResponsiveContainer: MockContainer,
    BarChart: MockContainer,
    Bar: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Cell: () => null,
    PieChart: MockContainer,
    Pie: () => null,
  };
});

const mockReport = {
  overall_detection_rate: 0.9134,
  total_revoked_providers: 335,
  total_revoked_cases: 862,
  detection_by_reason: [
    { reason: "Billing Abuse", count: 208, detected: 193, rate: 0.9279 },
    { reason: "Felony", count: 106, detected: 106, rate: 1.0 },
    { reason: "DME Standards", count: 164, detected: 106, rate: 0.6463 },
  ],
  baseline_flagging_rate: 0.5144,
  avg_blind_risk_revoked: 20.4,
  avg_risk_non_revoked: 41.4,
  detection_lift: 1.8,
  provider_level: { high_risk: 1, review: 305, stable: 29 },
  methodology:
    "Retrospective blind validation: revocation labels were withheld.",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Validation", () => {
  it("renders KPI cards with correct values", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(screen.getByText("Retrospective Validation")).toBeInTheDocument();
    });
    expect(screen.getAllByText(/91\.3%/).length).toBeGreaterThan(0);
    expect(screen.getByText("335")).toBeInTheDocument();
    expect(screen.getAllByText(/1\.8x/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/51\.4%/).length).toBeGreaterThan(0);
  });

  it("renders key insight callout", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(
        screen.getByText(/91.3% of revoked providers detected/),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/306 of 335/)).toBeInTheDocument();
  });

  it("renders comparison strip with lift", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(screen.getByText("1.8x more likely")).toBeInTheDocument();
    });
  });

  it("renders provider-level breakdown bars", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(screen.getByText("High Risk")).toBeInTheDocument();
    });
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("Stable (missed)")).toBeInTheDocument();
  });

  it("renders detection by reason chart data", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(
        screen.getByText("Detection Rate by Revocation Reason"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Billing Abuse")).toBeInTheDocument();
    expect(screen.getByText("Felony")).toBeInTheDocument();
  });

  it("renders methodology flow steps", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(screen.getByText("Remove Revocation Flag")).toBeInTheDocument();
    });
    expect(screen.getByText("Score on Behavior Alone")).toBeInTheDocument();
    expect(screen.getByText("Compare Against Outcomes")).toBeInTheDocument();
  });

  it("shows loading spinner initially", () => {
    vi.mocked(getValidation).mockReturnValue(new Promise(() => {}));
    const { container } = render(<Validation />);

    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    expect(screen.queryByText("91.3%")).not.toBeInTheDocument();
  });

  it("shows error state when API fails", async () => {
    vi.mocked(getValidation).mockRejectedValue(new Error("fail"));
    render(<Validation />);

    await waitFor(() => {
      expect(
        screen.getByText("Unable to load validation report."),
      ).toBeInTheDocument();
    });
  });

  it("renders detail table with reason rows", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(screen.getByText("92.8%")).toBeInTheDocument();
    });
    expect(screen.getByText("100.0%")).toBeInTheDocument();
    expect(screen.getByText("64.6%")).toBeInTheDocument();
  });

  it("renders donut chart legend", async () => {
    vi.mocked(getValidation).mockResolvedValue(mockReport);
    render(<Validation />);

    await waitFor(() => {
      expect(screen.getByText(/Detected \(306\)/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Missed \(29\)/)).toBeInTheDocument();
  });
});
