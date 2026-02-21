import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import LogConsole from "./LogConsole";

describe("LogConsole", () => {
  it("shows empty state when no logs", () => {
    render(<LogConsole logs={[]} onClear={vi.fn()} />);
    expect(screen.getByText("Waiting...")).toBeInTheDocument();
  });

  it("renders log messages", () => {
    const logs = [
      { id: 1, message: "Transcription lancee", color: null },
      { id: 2, message: "Erreur critique", color: "red" },
    ];
    render(<LogConsole logs={logs} onClear={vi.fn()} />);
    expect(screen.getByText("Transcription lancee")).toBeInTheDocument();
    expect(screen.getByText("Erreur critique")).toBeInTheDocument();
  });

  it("applies color to log lines", () => {
    const logs = [{ id: 1, message: "OK", color: "green" }];
    render(<LogConsole logs={logs} onClear={vi.fn()} />);
    expect(screen.getByText("OK")).toHaveStyle({ color: "rgb(0, 128, 0)" });
  });

  it("uses default color when no color specified", () => {
    const logs = [{ id: 1, message: "Info", color: null }];
    render(<LogConsole logs={logs} onClear={vi.fn()} />);
    expect(screen.getByText("Info")).toHaveStyle({ color: "#eeeeee" });
  });

  it("calls onClear when Effacer button is clicked", async () => {
    const onClear = vi.fn();
    render(<LogConsole logs={[]} onClear={onClear} />);
    await userEvent.click(screen.getByText("Clear"));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("hides empty state when logs exist", () => {
    const logs = [{ id: 1, message: "Hello", color: null }];
    render(<LogConsole logs={logs} onClear={vi.fn()} />);
    expect(screen.queryByText("Waiting...")).not.toBeInTheDocument();
  });
});
