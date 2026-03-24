import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../StatusBadge";

describe("StatusBadge", () => {
  it("renders risk band label from band prop", () => {
    render(<StatusBadge band="high_risk" />);
    // CSS uppercase makes it visual only — DOM text stays "High Risk"
    expect(screen.getByText("High Risk")).toBeInTheDocument();
  });

  it("renders custom label when provided", () => {
    render(<StatusBadge band="stable" label="Custom Label" />);
    expect(screen.getByText("Custom Label")).toBeInTheDocument();
  });

  it("applies sm size classes", () => {
    const { container } = render(<StatusBadge band="review" size="sm" />);
    const badge = container.querySelector("span")!;
    expect(badge.className).toContain("px-2");
    expect(badge.className).toContain("py-0.5");
    expect(badge.className).toContain("text-xs");
  });

  it("applies md (default) size classes", () => {
    const { container } = render(<StatusBadge band="review" />);
    const badge = container.querySelector("span")!;
    expect(badge.className).toContain("px-2.5");
    expect(badge.className).toContain("py-1");
    expect(badge.className).toContain("text-[11px]");
  });

  it("renders Unknown for null band", () => {
    render(<StatusBadge band={null} />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });

  it("applies rose colors for high_risk", () => {
    const { container } = render(<StatusBadge band="high_risk" />);
    const badge = container.querySelector("span")!;
    expect(badge.className).toContain("bg-rose-100");
    expect(badge.className).toContain("text-rose-700");
  });

  it("applies emerald colors for stable", () => {
    const { container } = render(<StatusBadge band="stable" />);
    const badge = container.querySelector("span")!;
    expect(badge.className).toContain("bg-emerald-100");
    expect(badge.className).toContain("text-emerald-700");
  });
});
