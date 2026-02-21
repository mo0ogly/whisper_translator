  import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "./App";

// Mock WebSocket
class MockWebSocket {
  constructor() {
    this.onmessage = null;
    this.onclose = null;
    this.close = vi.fn();
  }
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", MockWebSocket);
  vi.stubGlobal("fetch", vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ ffmpeg: true, ollama: true, pyannote: true }),
    })
  ));
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("renders the app title", () => {
    render(<App />);
    expect(screen.getByText("Translator")).toBeInTheDocument();
  });

  it("renders health status badges", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/FFmpeg OK/)).toBeInTheDocument();
      expect(screen.getByText(/Ollama OK/)).toBeInTheDocument();
      expect(screen.getByText(/Pyannote OK/)).toBeInTheDocument();
    });
  });

  it("shows error status when health check fails", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("fail"))));
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/FFmpeg missing/)).toBeInTheDocument();
      expect(screen.getByText(/Ollama offline/)).toBeInTheDocument();
      expect(screen.getByText(/Pyannote not configured/)).toBeInTheDocument();
    });
  });

  it("renders tab buttons", () => {
    render(<App />);
    expect(screen.getByText("Whisper Transcription")).toBeInTheDocument();
    expect(screen.getByText("Ollama Translation")).toBeInTheDocument();
  });

  it("defaults to transcription tab", () => {
    render(<App />);
    expect(screen.getByText("Audio/Video Transcription")).toBeInTheDocument();
  });

  it("switches to Ollama tab", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("Ollama Translation"));
    expect(screen.getByText("Ollama Translation", { selector: "h2" })).toBeInTheDocument();
    expect(screen.queryByText("Audio/Video Transcription")).not.toBeInTheDocument();
  });

  it("switches back to Transcription tab", async () => {
    render(<App />);
    await userEvent.click(screen.getByText("Ollama Translation"));
    await userEvent.click(screen.getByText("Whisper Transcription"));
    expect(screen.getByText("Audio/Video Transcription")).toBeInTheDocument();
  });

  it("renders the log console", () => {
    render(<App />);
    expect(screen.getByText("Console")).toBeInTheDocument();
    expect(screen.getByText("Waiting...")).toBeInTheDocument();
  });
});
