import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Analytics } from "../Analytics";
import { chat } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  chat: vi.fn(),
}));

vi.mock("recharts", () => {
  const MockContainer = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="recharts-mock">{children}</div>
  );
  return {
    ResponsiveContainer: MockContainer,
    BarChart: MockContainer,
    Bar: () => null,
    LineChart: MockContainer,
    Line: () => null,
    PieChart: MockContainer,
    Pie: () => null,
    Cell: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
  };
});

describe("Analytics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chat).mockResolvedValue({
      answer: "There are 12 flagged providers in CA.",
      sql: "select state, count(*) from provider_features group by state",
      duration_ms: 42,
      chart_spec: null,
      columns: ["state", "count"],
      rows: [{ state: "CA", count: 12 }],
      row_count: 1,
    });

    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("renders the empty state with the anchored composer controls", () => {
    const { container } = render(<Analytics />);

    expect(screen.getByText("Analytics")).toBeInTheDocument();
    expect(screen.getByText("Ask anything about the data")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Ask a question about the data"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Send analytics question" }),
    ).toBeInTheDocument();

    const panel = container.querySelector(
      ".flex.min-h-0.flex-1.flex-col.rounded-2xl.border",
    );
    const composerSection = container.querySelector(
      ".border-t.border-slate-200.bg-white",
    );

    expect(panel).toBeInTheDocument();
    expect(composerSection).toBeInTheDocument();
  });

  it("sends a suggestion and renders the response content", async () => {
    const user = userEvent.setup();
    render(<Analytics />);

    await user.click(
      screen.getByRole("button", {
        name: "How many providers are flagged as high risk by state?",
      }),
    );

    await waitFor(() => {
      expect(chat).toHaveBeenCalledWith(
        "How many providers are flagged as high risk by state?",
        [],
      );
    });

    expect(
      await screen.findByText("There are 12 flagged providers in CA."),
    ).toBeInTheDocument();
    expect(screen.getByText(/SQL Query \(42ms\)/)).toBeInTheDocument();
    expect(screen.getByText("1 rows")).toBeInTheDocument();
  });

  it("disables the send button for blank input and enables it for typed input", async () => {
    const user = userEvent.setup();
    render(<Analytics />);

    const input = screen.getByLabelText("Ask a question about the data");
    const button = screen.getByRole("button", {
      name: "Send analytics question",
    });

    expect(button).toBeDisabled();

    await user.type(input, "Show me average risk score by state");
    expect(button).toBeEnabled();
  });
});
