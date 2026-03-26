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
    Bar: ({ dataKey }: { dataKey?: string }) => <div data-testid="bar-series" data-key={String(dataKey)} />,
    LineChart: MockContainer,
    Line: ({ dataKey }: { dataKey?: string }) => <div data-testid="line-series" data-key={String(dataKey)} />,
    PieChart: MockContainer,
    Pie: ({ dataKey, nameKey }: { dataKey?: string; nameKey?: string }) => <div data-testid="pie-series" data-key={String(dataKey)} data-name-key={String(nameKey)} />,
    Cell: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
  };
});

function makeResponse(overrides: Partial<Awaited<ReturnType<typeof chat>>> = {}) {
  return {
    answer: "There are 12 flagged providers in CA.",
    sql: "select state, count(*) from provider_features group by state",
    duration_ms: 42,
    chart_spec: null,
    columns: ["state", "count"],
    rows: [{ state: "CA", count: 12 }],
    row_count: 1,
    ...overrides,
  };
}

describe("Analytics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chat).mockResolvedValue(makeResponse());

    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("renders the empty state with the anchored composer controls", () => {
    const { container } = render(<Analytics />);

    expect(screen.getByText("AI Assistant")).toBeInTheDocument();
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

  it("submits typed input with Enter", async () => {
    const user = userEvent.setup();
    render(<Analytics />);

    const input = screen.getByLabelText("Ask a question about the data");
    await user.type(input, "Show total providers{Enter}");

    await waitFor(() => {
      expect(chat).toHaveBeenCalledWith("Show total providers", []);
    });
    expect(await screen.findByText("Show total providers")).toBeInTheDocument();
  });

  it("passes prior history on a follow-up question", async () => {
    const user = userEvent.setup();
    vi.mocked(chat)
      .mockResolvedValueOnce(
        makeResponse({
          answer: "Florida has 5 flagged providers.",
          rows: [{ state: "FL", count: 5 }],
        }),
      )
      .mockResolvedValueOnce(
        makeResponse({
          answer: "Texas has 9 flagged providers.",
          rows: [{ state: "TX", count: 9 }],
        }),
      );

    render(<Analytics />);
    const input = screen.getByLabelText("Ask a question about the data");

    await user.type(input, "How many in Florida?{Enter}");
    expect(
      await screen.findByText("Florida has 5 flagged providers."),
    ).toBeInTheDocument();

    await user.type(input, "What about Texas?{Enter}");

    await waitFor(() => {
      expect(chat).toHaveBeenNthCalledWith(2, "What about Texas?", [
        { role: "user", content: "How many in Florida?" },
        { role: "assistant", content: "Florida has 5 flagged providers." },
      ]);
    });
  });

  it("shows a loading state and blocks duplicate sends", async () => {
    const user = userEvent.setup();
    let resolveChat: ((value: ReturnType<typeof makeResponse>) => void) | undefined;
    vi.mocked(chat).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveChat = resolve;
        }),
    );

    render(<Analytics />);

    await user.click(
      screen.getByRole("button", {
        name: "Compare the top 5 specialties by flagging rate",
      }),
    );

    expect(await screen.findByText("Thinking...")).toBeInTheDocument();
    expect(chat).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("button", { name: "Send analytics question" }),
    ).toBeDisabled();

    resolveChat?.(makeResponse({ answer: "Done loading." }));
    expect(await screen.findByText("Done loading.")).toBeInTheDocument();
  });

  it("renders a bar chart response", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockResolvedValueOnce(
      makeResponse({
        answer: "Here is the bar chart.",
        sql: null,
        chart_spec: {
          type: "bar",
          title: "Providers by State",
          xKey: "state",
          yKey: "count",
          data: [
            { state: "CA", count: 12 },
            { state: "TX", count: 9 },
          ],
        },
        rows: [],
        row_count: 0,
        columns: [],
      }),
    );

    render(<Analytics />);
    await user.click(
      screen.getByRole("button", {
        name: "How many providers are flagged as high risk by state?",
      }),
    );

    expect(await screen.findByText("Providers by State")).toBeInTheDocument();
    expect(screen.getAllByTestId("recharts-mock").length).toBeGreaterThan(0);
    expect(screen.queryByText(/SQL Query/)).not.toBeInTheDocument();
  });

  it("renders a line chart response", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockResolvedValueOnce(
      makeResponse({
        answer: "Here is the trend line.",
        chart_spec: {
          type: "line",
          title: "Monthly Trend",
          xKey: "month",
          yKey: "count",
          data: [
            { month: "Jan", count: 2 },
            { month: "Feb", count: 5 },
          ],
        },
      }),
    );

    render(<Analytics />);
    await user.click(
      screen.getByRole("button", {
        name: "Show me the average risk score by provider type",
      }),
    );

    expect(await screen.findByText("Monthly Trend")).toBeInTheDocument();
  });

  it("renders a pie chart response", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockResolvedValueOnce(
      makeResponse({
        answer: "Here is the specialty split.",
        chart_spec: {
          type: "pie",
          title: "Specialty Share",
          nameKey: "name",
          valueKey: "value",
          data: [
            { name: "Cardiology", value: 8 },
            { name: "Internal Medicine", value: 12 },
          ],
        },
      }),
    );

    render(<Analytics />);
    await user.click(
      screen.getByRole("button", {
        name: "Compare the top 5 specialties by flagging rate",
      }),
    );

    expect(await screen.findByText("Specialty Share")).toBeInTheDocument();
  });

  it("uses bar chart fallback keys when xKey and yKey are omitted", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockResolvedValueOnce(
      makeResponse({
        answer: "Fallback bar chart.",
        chart_spec: {
          type: "bar",
          title: "Fallback Bar",
          nameKey: "label",
          valueKey: "total",
          data: [
            { label: "CA", total: 12 },
            { label: "TX", total: 9 },
          ],
        },
        rows: [],
        row_count: 0,
        columns: [],
        sql: null,
      }),
    );

    render(<Analytics />);
    await user.click(screen.getByRole("button", { name: "What are the most common HCPCS codes among high-risk providers?" }));

    expect(await screen.findByText("Fallback Bar")).toBeInTheDocument();
    expect(screen.getByTestId("bar-series")).toHaveAttribute("data-key", "total");
  });

  it("uses line chart default keys when no explicit keys are provided", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockResolvedValueOnce(
      makeResponse({
        answer: "Default line chart.",
        chart_spec: {
          type: "line",
          title: "Fallback Line",
          data: [
            { name: "Jan", value: 2 },
            { name: "Feb", value: 5 },
          ],
        },
      }),
    );

    render(<Analytics />);
    await user.click(screen.getByRole("button", { name: "Show me the average risk score by provider type" }));

    expect(await screen.findByText("Fallback Line")).toBeInTheDocument();
    expect(screen.getByTestId("line-series")).toHaveAttribute("data-key", "value");
  });

  it("uses pie chart default keys when no explicit keys are provided", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockResolvedValueOnce(
      makeResponse({
        answer: "Default pie chart.",
        chart_spec: {
          type: "pie",
          title: "Fallback Pie",
          data: [
            { name: "Cardiology", value: 8 },
            { name: "Internal Medicine", value: 12 },
          ],
        },
      }),
    );

    render(<Analytics />);
    await user.click(screen.getByRole("button", { name: "Compare the top 5 specialties by flagging rate" }));

    expect(await screen.findByText("Fallback Pie")).toBeInTheDocument();
    expect(screen.getByTestId("pie-series")).toHaveAttribute("data-key", "value");
    expect(screen.getByTestId("pie-series")).toHaveAttribute("data-name-key", "name");
  });

  it("shows the error message from Error rejections", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockRejectedValueOnce(new Error("Query failed"));

    render(<Analytics />);
    const input = screen.getByLabelText("Ask a question about the data");
    await user.type(input, "Bad query{Enter}");

    expect(await screen.findByText("Error: Query failed")).toBeInTheDocument();
  });

  it("shows a generic message for non-Error rejections", async () => {
    const user = userEvent.setup();
    vi.mocked(chat).mockRejectedValueOnce("boom");

    render(<Analytics />);
    const input = screen.getByLabelText("Ask a question about the data");
    await user.type(input, "Another bad query{Enter}");

    expect(
      await screen.findByText("Something went wrong."),
    ).toBeInTheDocument();
  });
});
