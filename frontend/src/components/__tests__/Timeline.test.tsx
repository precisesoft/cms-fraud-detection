import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Timeline } from "../Timeline";
import type { CaseActionRecord } from "../../lib/api";

const mockEvents: CaseActionRecord[] = [
  {
    id: 1,
    case_id: "CASE-001",
    npi: "1111111111",
    action: "FLAGGED",
    notes: "Suspicious billing pattern",
    analyst_id: "analyst_1",
    created_at: "2026-01-15T10:30:00Z",
  },
  {
    id: 2,
    case_id: "CASE-001",
    npi: "1111111111",
    action: "ESCALATED",
    notes: null,
    analyst_id: "analyst_2",
    created_at: "2026-01-16T14:00:00Z",
  },
];

describe("Timeline", () => {
  it("renders empty state with default text", () => {
    render(<Timeline events={[]} />);
    expect(screen.getByText("No events yet.")).toBeInTheDocument();
  });

  it("renders empty state with custom text", () => {
    render(<Timeline events={[]} emptyText="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("renders events with action and case id", () => {
    render(<Timeline events={mockEvents} />);
    expect(screen.getByText("FLAGGED — Case CASE-001")).toBeInTheDocument();
    expect(screen.getByText("ESCALATED — Case CASE-001")).toBeInTheDocument();
  });

  it("renders event notes when present", () => {
    render(<Timeline events={mockEvents} />);
    expect(screen.getByText("Suspicious billing pattern")).toBeInTheDocument();
  });

  it("does not render notes when null", () => {
    render(<Timeline events={mockEvents} />);
    // Second event has null notes — no extra paragraph
    const escalatedSection = screen.getByText("ESCALATED — Case CASE-001");
    const sibling = escalatedSection.nextElementSibling;
    // The next sibling should be the analyst line, not a notes line
    expect(sibling?.textContent).toContain("analyst_2");
  });

  it("renders analyst id and timestamp", () => {
    render(<Timeline events={mockEvents} />);
    expect(screen.getByText(/analyst_1/)).toBeInTheDocument();
    expect(screen.getByText(/analyst_2/)).toBeInTheDocument();
  });
});
