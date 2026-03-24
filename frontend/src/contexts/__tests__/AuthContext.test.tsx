import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../AuthContext";

// Mock the entire api module
vi.mock("../../lib/api", () => ({
  getToken: vi.fn(),
  getMe: vi.fn(),
  login: vi.fn(),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}));

import {
  getToken,
  getMe,
  login as apiLogin,
  setToken,
  clearToken,
} from "../../lib/api";

const mockGetToken = vi.mocked(getToken);
const mockGetMe = vi.mocked(getMe);
const mockApiLogin = vi.mocked(apiLogin);
const mockSetToken = vi.mocked(setToken);
const mockClearToken = vi.mocked(clearToken);

const mockUser = {
  id: 1,
  username: "analyst",
  role: "analyst",
  full_name: "Test Analyst",
};

beforeEach(() => {
  vi.clearAllMocks();
  // Default: no existing token — no loading on mount
  mockGetToken.mockReturnValue(null);
});

describe("AuthProvider / useAuth", () => {
  it("starts with no loading when there is no stored token", () => {
    mockGetToken.mockReturnValue(null);
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });

  it("starts loading when a stored token exists", () => {
    mockGetToken.mockReturnValue("existing-token");
    mockGetMe.mockReturnValue(new Promise(() => {})); // never resolves

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    expect(result.current.isLoading).toBe(true);
  });

  it("hydrates user successfully when getMe resolves", async () => {
    mockGetToken.mockReturnValue("existing-token");
    mockGetMe.mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("clears token and stops loading when getMe rejects", async () => {
    mockGetToken.mockReturnValue("bad-token");
    mockGetMe.mockRejectedValue(new Error("401 Unauthorized"));

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockClearToken).toHaveBeenCalledOnce();
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("sets user and token on successful login", async () => {
    mockGetToken.mockReturnValue(null);
    mockApiLogin.mockResolvedValue({
      access_token: "new-token",
      token_type: "bearer",
      user: mockUser,
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await act(async () => {
      await result.current.login("analyst", "password123");
    });

    expect(mockApiLogin).toHaveBeenCalledWith("analyst", "password123");
    expect(mockSetToken).toHaveBeenCalledWith("new-token");
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("propagates login errors to the caller", async () => {
    mockGetToken.mockReturnValue(null);
    mockApiLogin.mockRejectedValue(new Error("Invalid credentials"));

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await expect(
      act(async () => {
        await result.current.login("analyst", "wrongpass");
      }),
    ).rejects.toThrow("Invalid credentials");

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("clears user and token on logout", async () => {
    mockGetToken.mockReturnValue("existing-token");
    mockGetMe.mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

    act(() => {
      result.current.logout();
    });

    expect(mockClearToken).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("isAuthenticated is false when user is null", () => {
    mockGetToken.mockReturnValue(null);
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    expect(result.current.isAuthenticated).toBe(false);
  });

  it("throws when useAuth is called outside of AuthProvider", () => {
    // Suppress the expected React error boundary console output
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within AuthProvider");

    consoleError.mockRestore();
  });
});
