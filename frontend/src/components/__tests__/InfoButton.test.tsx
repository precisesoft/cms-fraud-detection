import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InfoButton } from "../InfoButton";

function renderInfoButton() {
  return render(
    <InfoButton title="Risk Distribution">
      Shows how providers fall into three risk bands.
    </InfoButton>,
  );
}

describe("InfoButton", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders info icon button", () => {
    renderInfoButton();
    expect(
      screen.getByRole("button", { name: /Info: Risk Distribution/i }),
    ).toBeInTheDocument();
  });

  it("opens modal on click", async () => {
    const user = userEvent.setup();
    renderInfoButton();
    await user.click(screen.getByRole("button", { name: /Info: Risk Distribution/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows title and description in modal", async () => {
    const user = userEvent.setup();
    renderInfoButton();
    await user.click(screen.getByRole("button", { name: /Info: Risk Distribution/i }));
    expect(screen.getByText("Risk Distribution")).toBeInTheDocument();
    expect(
      screen.getByText("Shows how providers fall into three risk bands."),
    ).toBeInTheDocument();
  });

  it("closes on X button click", async () => {
    const user = userEvent.setup();
    renderInfoButton();
    await user.click(screen.getByRole("button", { name: /Info: Risk Distribution/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Close/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes on ESC key", async () => {
    const user = userEvent.setup();
    renderInfoButton();
    await user.click(screen.getByRole("button", { name: /Info: Risk Distribution/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes on backdrop click", async () => {
    const user = userEvent.setup();
    const { container } = renderInfoButton();
    await user.click(screen.getByRole("button", { name: /Info: Risk Distribution/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    // The backdrop is the fixed overlay div; click outside the panel
    const backdrop = container.querySelector(".fixed.inset-0")!;
    await user.click(backdrop);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("has role=dialog and aria-modal=true", async () => {
    const user = userEvent.setup();
    renderInfoButton();
    await user.click(screen.getByRole("button", { name: /Info: Risk Distribution/i }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  it("returns focus to trigger button on close", async () => {
    const user = userEvent.setup();
    renderInfoButton();
    const trigger = screen.getByRole("button", { name: /Info: Risk Distribution/i });
    await user.click(trigger);
    await user.click(screen.getByRole("button", { name: /Close/i }));
    expect(document.activeElement).toBe(trigger);
  });
});
