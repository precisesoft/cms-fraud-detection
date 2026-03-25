import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AssistantDrawer } from "../AssistantDrawer";
import { chat } from "../../lib/api";
import type { ChatResponse } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  chat: vi.fn(),
}));

const defaultContext = { type: "provider", entityId: "NPI-001", label: "Acme" };

const mockResponse: ChatResponse = {
  answer: "The top risk signal is high service volume.",
  sql: "SELECT * FROM claims WHERE npi = '123'",
  columns: ["npi", "score"],
  rows: [{ npi: "123", score: 85 }],
  row_count: 1,
  duration_ms: 42,
  chart_spec: null,
};

function renderDrawer(isOpen = true) {
  const onClose = vi.fn();
  const result = render(
    <AssistantDrawer
      isOpen={isOpen}
      onClose={onClose}
      context={defaultContext}
    />,
  );
  return { ...result, onClose };
}

describe("AssistantDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(chat).mockResolvedValue(mockResponse);
  });

  it("renders nothing when closed", () => {
    const { container } = renderDrawer(false);
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it("renders dialog when open", () => {
    renderDrawer();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Investigation Assistant"),
    ).toBeInTheDocument();
  });

  it("has aria-modal attribute", () => {
    renderDrawer();
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  });

  it("shows context label in header", () => {
    renderDrawer();
    expect(screen.getByText(/provider · Acme/)).toBeInTheDocument();
  });

  it("renders suggested prompts for provider context", () => {
    renderDrawer();
    expect(
      screen.getByText("What are the top risk signals for this provider?"),
    ).toBeInTheDocument();
  });

  it("close button has aria-label", () => {
    renderDrawer();
    expect(screen.getByLabelText("Close assistant")).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDrawer();
    await user.click(screen.getByLabelText("Close assistant"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when backdrop clicked", async () => {
    const user = userEvent.setup();
    const { onClose, container } = renderDrawer();
    // Backdrop is the first fixed div with bg-slate-900/20
    const backdrop = container.querySelector(".fixed.inset-0.z-50");
    expect(backdrop).not.toBeNull();
    await user.click(backdrop!);
    expect(onClose).toHaveBeenCalled();
  });

  it("sends a message and displays response", async () => {
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "What is the risk?");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(chat).toHaveBeenCalledWith("What is the risk?", [], "NPI-001");
    });
    await waitFor(() => {
      expect(
        screen.getByText("The top risk signal is high service volume."),
      ).toBeInTheDocument();
    });
  });

  it("displays SQL block in response", async () => {
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Show query");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(
        screen.getByText("SELECT * FROM claims WHERE npi = '123'"),
      ).toBeInTheDocument();
    });
  });

  it("displays result table with columns and rows", async () => {
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Show data");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("npi")).toBeInTheDocument();
      expect(screen.getByText("score")).toBeInTheDocument();
      expect(screen.getByText("123")).toBeInTheDocument();
      expect(screen.getByText("85")).toBeInTheDocument();
    });
  });

  it("sends message when suggested prompt is clicked", async () => {
    const user = userEvent.setup();
    renderDrawer();
    await user.click(
      screen.getByText("What are the top risk signals for this provider?"),
    );
    await waitFor(() => {
      expect(chat).toHaveBeenCalledWith(
        "What are the top risk signals for this provider?",
        [],
        "NPI-001",
      );
    });
  });

  it("shows error message on API failure", async () => {
    vi.mocked(chat).mockRejectedValue(new Error("Network error"));
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Fail please");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("shows generic error for non-Error throws", async () => {
    vi.mocked(chat).mockRejectedValue("something");
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Fail again");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("Request failed.")).toBeInTheDocument();
    });
  });

  it("clears messages when Clear Thread is clicked", async () => {
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Hello");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(
        screen.getByText("The top risk signal is high service volume."),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByText("Clear Thread"));
    expect(
      screen.queryByText("The top risk signal is high service volume."),
    ).not.toBeInTheDocument();
  });

  it("does not send empty message", async () => {
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.click(textarea);
    await user.keyboard("{Enter}");
    expect(chat).not.toHaveBeenCalled();
  });

  it("shows thinking indicator while loading", async () => {
    let resolveChat!: (v: ChatResponse) => void;
    vi.mocked(chat).mockReturnValue(
      new Promise((r) => {
        resolveChat = r;
      }),
    );
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Slow query");
    await user.keyboard("{Enter}");
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
    resolveChat(mockResponse);
    await waitFor(() => {
      expect(screen.queryByText("Thinking...")).not.toBeInTheDocument();
    });
  });

  it("table headers have scope=col", async () => {
    const user = userEvent.setup();
    const { container } = renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Query");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("npi")).toBeInTheDocument();
    });
    const ths = container.querySelectorAll("th[scope='col']");
    expect(ths.length).toBe(2); // npi, score
  });

  it("shows rows truncation message for >10 rows", async () => {
    const bigResponse: ChatResponse = {
      ...mockResponse,
      rows: Array.from({ length: 15 }, (_, i) => ({
        npi: String(i),
        score: i,
      })),
      row_count: 15,
    };
    vi.mocked(chat).mockResolvedValue(bigResponse);
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Big result");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("Showing 10 of 15 rows")).toBeInTheDocument();
    });
  });

  it("calls onClose on Escape key", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDrawer();
    const dialog = screen.getByRole("dialog");
    dialog.focus();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("sends message via send button click", async () => {
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Via button");
    // The send button has no text label — find it by class
    const buttons = screen.getAllByRole("button");
    const sendBtn = buttons.find(
      (b) => b.querySelector("svg") && b.className.includes("bg-indigo-600"),
    );
    expect(sendBtn).toBeDefined();
    await user.click(sendBtn!);
    await waitFor(() => {
      expect(chat).toHaveBeenCalledWith("Via button", [], "NPI-001");
    });
  });

  it("does not send while already loading", async () => {
    let resolveChat!: (v: ChatResponse) => void;
    vi.mocked(chat).mockReturnValue(
      new Promise((r) => {
        resolveChat = r;
      }),
    );
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "First");
    await user.keyboard("{Enter}");
    expect(chat).toHaveBeenCalledTimes(1);
    // Try to send again while loading — should be blocked
    await user.type(textarea, "Second");
    await user.keyboard("{Enter}");
    expect(chat).toHaveBeenCalledTimes(1);
    resolveChat(mockResponse);
  });

  it("renders response without sql when sql is null", async () => {
    vi.mocked(chat).mockResolvedValue({
      ...mockResponse,
      sql: null as unknown as string,
      rows: [],
      columns: [],
      row_count: 0,
    });
    const user = userEvent.setup();
    renderDrawer();
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "No sql");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(
        screen.getByText("The top risk signal is high service volume."),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText("SQL")).not.toBeInTheDocument();
  });

  it("passes undefined npi when entityId is empty", async () => {
    vi.mocked(chat).mockResolvedValue(mockResponse);
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <AssistantDrawer
        isOpen={true}
        onClose={onClose}
        context={{ type: "provider", entityId: "", label: "Empty" }}
      />,
    );
    const textarea = screen.getByPlaceholderText("Ask about this provider...");
    await user.type(textarea, "Test query");
    await user.keyboard("{Enter}");
    await waitFor(() => {
      expect(chat).toHaveBeenCalledWith("Test query", [], undefined);
    });
  });

});
