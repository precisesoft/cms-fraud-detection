import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Login } from "../Login";
import { useAuth } from "../../contexts/AuthContext";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockUseAuth = vi.mocked(useAuth);

// Default unauthenticated state shared across tests
const defaultAuthState = {
  login: vi.fn(),
  logout: vi.fn(),
  isAuthenticated: false,
  isLoading: false,
  user: null,
};

function renderLogin(authOverrides = {}) {
  mockUseAuth.mockReturnValue({ ...defaultAuthState, ...authOverrides });

  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>Dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Login page", () => {
  it("renders username and password fields and the submit button", () => {
    renderLogin();

    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("redirects to / when the user is already authenticated", () => {
    renderLogin({ isAuthenticated: true });

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.queryByLabelText("Username")).not.toBeInTheDocument();
  });

  it("calls login with typed credentials on form submit", async () => {
    const user = userEvent.setup();
    const mockLogin = vi.fn().mockResolvedValue(undefined);
    renderLogin({ login: mockLogin });

    await user.type(screen.getByLabelText("Username"), "analyst");
    await user.type(screen.getByLabelText("Password"), "secret123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("analyst", "secret123");
    });
  });

  it("displays an error message when login fails", async () => {
    const user = userEvent.setup();
    const mockLogin = vi.fn().mockRejectedValue(new Error("401"));
    renderLogin({ login: mockLogin });

    await user.type(screen.getByLabelText("Username"), "analyst");
    await user.type(screen.getByLabelText("Password"), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Invalid username or password"),
      ).toBeInTheDocument();
    });
  });

  it("shows 'Signing in...' on the button while the request is in flight", async () => {
    const user = userEvent.setup();
    // login resolves after a short delay so we can observe the loading state
    const mockLogin = vi.fn(
      () => new Promise((resolve) => setTimeout(resolve, 200)),
    );
    renderLogin({ login: mockLogin });

    await user.type(screen.getByLabelText("Username"), "analyst");
    await user.type(screen.getByLabelText("Password"), "pass");

    // Start submit but don't await it
    user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /signing in/i }),
      ).toBeInTheDocument();
    });

    // Wait for completion to avoid act() warnings
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /^sign in$/i }),
      ).toBeInTheDocument();
    });
  });

  it("username and password inputs are marked required", () => {
    renderLogin();

    expect(screen.getByLabelText("Username")).toBeRequired();
    expect(screen.getByLabelText("Password")).toBeRequired();
  });

  it("does not display an error message before any submission attempt", () => {
    renderLogin();

    expect(
      screen.queryByText("Invalid username or password"),
    ).not.toBeInTheDocument();
  });
});
