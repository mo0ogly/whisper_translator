import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TranscriptionPanel from "./TranscriptionPanel";

describe("TranscriptionPanel", () => {
  let addLog, setProgress;

  beforeEach(() => {
    addLog = vi.fn();
    setProgress = vi.fn();
  });

  it("renders the panel title", () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    expect(screen.getByText("Audio/Video Transcription")).toBeInTheDocument();
  });

  it("renders model select with all options", () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    const models = ["tiny", "base", "small", "medium", "large", "large-v2"];
    models.forEach((m) => {
      expect(screen.getByRole("option", { name: m })).toBeInTheDocument();
    });
  });

  it("defaults to medium model", () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    const select = screen.getByDisplayValue("medium");
    expect(select).toBeInTheDocument();
  });

  it("renders language selects", () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    expect(screen.getByText("Audio Language")).toBeInTheDocument();
    expect(screen.getByText("Target Language")).toBeInTheDocument();
  });

  it("disables transcribe button when no files selected", () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    expect(screen.getByText("Transcribe")).toBeDisabled();
  });

  it("shows file after selection via input", async () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    const input = document.querySelector("input[type='file']");
    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    await userEvent.upload(input, file);
    expect(screen.getByText(/test\.mp3/)).toBeInTheDocument();
  });

  it("removes file when clicking remove button", async () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    const input = document.querySelector("input[type='file']");
    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    await userEvent.upload(input, file);
    expect(screen.getByText(/test\.mp3/)).toBeInTheDocument();
    await userEvent.click(screen.getByText("✕"));
    expect(screen.queryByText(/test\.mp3/)).not.toBeInTheDocument();
  });

  it("allows changing model selection", async () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    const select = screen.getByDisplayValue("medium");
    await userEvent.selectOptions(select, "large");
    expect(select).toHaveValue("large");
  });

  it("shows drag-and-drop hint with accepted formats", () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    expect(screen.getByText("MP4, MP3, WAV, M4A, FLAC, OGG, WebM")).toBeInTheDocument();
  });

  it("renders diarization checkbox", () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    expect(screen.getByText(/speaker diarization/i)).toBeInTheDocument();
  });

  it("shows detect speakers button when diarization enabled and file added", async () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    await userEvent.click(screen.getByText(/speaker diarization/i));
    const input = document.querySelector("input[type='file']");
    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    await userEvent.upload(input, file);
    expect(screen.getByText("Detect Speakers")).toBeInTheDocument();
  });

  it("disables transcribe when diarization enabled but not detected", async () => {
    render(<TranscriptionPanel addLog={addLog} setProgress={setProgress} />);
    await userEvent.click(screen.getByText(/speaker diarization/i));
    const input = document.querySelector("input[type='file']");
    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    await userEvent.upload(input, file);
    expect(screen.getByText("Transcribe")).toBeDisabled();
  });
});
