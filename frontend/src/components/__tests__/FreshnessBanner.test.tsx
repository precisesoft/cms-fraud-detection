import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { FreshnessBanner } from "../FreshnessBanner";
import { getIngestStatus } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  getIngestStatus: vi.fn(),
}));

let mockRole = "analyst";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, username: "testuser", role: mockRole, full_name: "Test User" },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const mockStatus = {
  sources: [
    { type: "Part B", version: "2024", uploaded_at: "2026-01-01T00:00:00Z", row_count: 100000 },
    { type: "Enrollment", version: "Q1-2026", uploaded_at: "2026-01-15T00:00:00Z", row_count: 50000 },
    { type: "Revocations", version: "Q2-2026", uploaded_at: "2026-04-01T00:00:00Z", row_count: 1500 },
  ],
  last_recalibration: {
    run_id: 42,
    completed_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
    providers_scored: 18412,
    status: "completed",
  },
  providers_in_system: 18412,
};

function renderBanner() {
  return render(
    <MemoryRouter>
      <FreshnessBanner />
    </MemoryRouter>,
  );
}

describe("FreshnessBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRole = "analyst";
  });

  it("renders nothing when API returns an error (graceful fallback)", async () => {
    vi.mocked(getIngestStatus).mockRejectedValue(new Error("404 Not Found"));
    const { container } = renderBanner();
    // Give the promise a chance to settle
    await new Promise((r) => setTimeout(r, 50));
    expect(container.firstChild).toBeNull();
  });

  it("renders source versions after API resolves", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue(mockStatus);
    renderBanner();
    await waitFor(() => {
      expect(screen.getByText(/Part B 2024/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Enrollment Q1-2026/)).toBeInTheDocument();
    expect(screen.getByText(/Revocations Q2-2026/)).toBeInTheDocument();
  });

  it("renders absolute recalibration date", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue(mockStatus);
    renderBanner();
    await waitFor(() => {
      // The date formatted as "Mon DD, YYYY"
      expect(screen.getByText(/Scores recalibrated:/)).toBeInTheDocument();
    });
  });

  it("renders relative time alongside absolute date", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue(mockStatus);
    renderBanner();
    await waitFor(() => {
      expect(screen.getByText(/3 days ago/)).toBeInTheDocument();
    });
  });

  it("renders provider count", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue(mockStatus);
    renderBanner();
    await waitFor(() => {
      expect(screen.getByText(/18,412 providers/)).toBeInTheDocument();
    });
  });

  it("shows green dot for fresh data (< 90 days)", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue(mockStatus); // 3 days ago → green
    renderBanner();
    await waitFor(() => {
      const dot = screen.getByLabelText("Fresh");
      expect(dot.className).toContain("bg-emerald-500");
    });
  });

  it("shows amber dot when approaching staleness (> 90 days)", async () => {
    const staleStatus = {
      ...mockStatus,
      last_recalibration: {
        ...mockStatus.last_recalibration,
        completed_at: new Date(Date.now() - 100 * 24 * 60 * 60 * 1000).toISOString(),
      },
    };
    vi.mocked(getIngestStatus).mockResolvedValue(staleStatus);
    renderBanner();
    await waitFor(() => {
      const dot = screen.getByLabelText("Approaching staleness");
      expect(dot.className).toContain("bg-amber-500");
    });
  });

  it("shows red dot when stale (> 180 days)", async () => {
    const veryStaleStatus = {
      ...mockStatus,
      last_recalibration: {
        ...mockStatus.last_recalibration,
        completed_at: new Date(Date.now() - 200 * 24 * 60 * 60 * 1000).toISOString(),
      },
    };
    vi.mocked(getIngestStatus).mockResolvedValue(veryStaleStatus);
    renderBanner();
    await waitFor(() => {
      const dot = screen.getByLabelText("Stale");
      expect(dot.className).toContain("bg-rose-500");
    });
  });

  it("shows red dot when no recalibration on record", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue({
      ...mockStatus,
      last_recalibration: null,
    });
    renderBanner();
    await waitFor(() => {
      const dot = screen.getByLabelText("Stale");
      expect(dot.className).toContain("bg-rose-500");
    });
    expect(screen.getByText("No recalibration on record")).toBeInTheDocument();
  });

  it("hides admin buttons for analyst role", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue(mockStatus);
    renderBanner();
    await waitFor(() => {
      expect(screen.getByText(/Part B 2024/)).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("Recalibrate scores")).toBeNull();
    expect(screen.queryByLabelText("Upload data")).toBeNull();
  });
});

describe("FreshnessBanner admin role", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRole = "admin";
  });

  it("shows admin buttons when user role is admin", async () => {
    vi.mocked(getIngestStatus).mockResolvedValue(mockStatus);
    render(
      <MemoryRouter>
        <FreshnessBanner />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Recalibrate scores")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Upload data")).toBeInTheDocument();
  });
});
