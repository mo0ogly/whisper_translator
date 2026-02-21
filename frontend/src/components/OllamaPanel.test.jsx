import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import OllamaPanel from "./OllamaPanel";

describe("OllamaPanel", () => {
  const addLog = vi.fn();

  it("renders the panel title", () => {
    render(<OllamaPanel addLog={addLog} />);
    expect(screen.getByText("Ollama Translation")).toBeInTheDocument();
  });

  it("renders SRT and Text sub-tabs", () => {
    render(<OllamaPanel addLog={addLog} />);
    expect(screen.getByText("SRT Subtitles")).toBeInTheDocument();
    expect(screen.getByText("Plain Text")).toBeInTheDocument();
  });

  it("defaults to SRT sub-tab", () => {
    render(<OllamaPanel addLog={addLog} />);
    const srtBtn = screen.getByText("SRT Subtitles");
    expect(srtBtn.className).toContain("active");
  });

  it("switches to Text sub-tab", async () => {
    render(<OllamaPanel addLog={addLog} />);
    await userEvent.click(screen.getByText("Plain Text"));
    const textBtn = screen.getByText("Plain Text");
    expect(textBtn.className).toContain("active");
  });

  it("renders language selects", () => {
    render(<OllamaPanel addLog={addLog} />);
    expect(screen.getByText("Source Language")).toBeInTheDocument();
    expect(screen.getByText("Target Language")).toBeInTheDocument();
  });

  it("shows all language options", () => {
    render(<OllamaPanel addLog={addLog} />);
    const langs = ["English", "French", "Spanish", "German", "Italian", "Japanese", "Chinese"];
    langs.forEach((lang) => {
      expect(screen.getAllByRole("option", { name: lang }).length).toBeGreaterThan(0);
    });
  });

  it("disables translate button when no file selected", () => {
    render(<OllamaPanel addLog={addLog} />);
    expect(screen.getByText("Translate with Ollama")).toBeDisabled();
  });

  it("shows correct drop zone text for SRT mode", () => {
    render(<OllamaPanel addLog={addLog} />);
    expect(screen.getByText(/SRT file/)).toBeInTheDocument();
  });

  it("shows correct drop zone text for Text mode", async () => {
    render(<OllamaPanel addLog={addLog} />);
    await userEvent.click(screen.getByText("Plain Text"));
    expect(screen.getByText(/text file/)).toBeInTheDocument();
  });
});
