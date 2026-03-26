import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Layout } from "../Layout";
import { useAuth } from "../../contexts/AuthContext";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockUseAuth = vi.mocked(useAuth);

function renderLayout(initialEntry = "/") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<div>Dashboard page</div>} />
          <Route path="providers" element={<div>Providers page</div>} />
          <Route path="claims" element={<div>Claims page</div>} />
          <Route
            path="investigations"
            element={<div>Investigations page</div>}
          />
          <Route path="risk-map" element={<div>Risk Map page</div>} />
          <Route path="analytics" element={<div>AI Assistant page</div>} />
          <Route path="simulate" element={<div>Simulate page</div>} />
          <Route path="fairness" element={<div>Fairness page</div>} />
          <Route path="data" element={<div>Data page</div>} />
          <Route path="live" element={<div>Live page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("Layout", () => {
  it("shows the reordered primary navigation for analyst users", () => {
    mockUseAuth.mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: 1,
        username: "analyst",
        role: "analyst",
        full_name: "Analyst User",
      },
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderLayout();

    const nav = screen.getByRole("navigation", { name: "Primary" });
    const labels = within(nav)
      .getAllByRole("link")
      .map((link) => link.textContent?.trim());

    expect(labels).toEqual([
      "Dashboard",
      "Providers",
      "Claims",
      "Investigations",
      "Risk Map",
      "AI Assistant",
      "Simulate",
      "Fairness",
    ]);
    expect(within(nav).queryByRole("link", { name: "Live Monitor" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: "Data" })).not.toBeInTheDocument();
  });

  it("shows Data at the end of the primary navigation for admin users", () => {
    mockUseAuth.mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      user: {
        id: 2,
        username: "admin",
        role: "admin",
        full_name: "Admin User",
      },
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderLayout();

    const nav = screen.getByRole("navigation", { name: "Primary" });
    const labels = within(nav)
      .getAllByRole("link")
      .map((link) => link.textContent?.trim());

    expect(labels).toEqual([
      "Dashboard",
      "Providers",
      "Claims",
      "Investigations",
      "Risk Map",
      "AI Assistant",
      "Simulate",
      "Fairness",
      "Data",
    ]);
  });
});
