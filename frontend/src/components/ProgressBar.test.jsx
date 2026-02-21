import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ProgressBar from "./ProgressBar";

describe("ProgressBar", () => {
  it("renders nothing when total is 0", () => {
    const { container } = render(
      <ProgressBar current={0} total={0} percent={0} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders file-based progress when total <= 10", () => {
    render(<ProgressBar current={2} total={5} percent={40} />);
    expect(screen.getByText("File 2 of 5 (40%)")).toBeInTheDocument();
  });

  it("renders time-based progress when total > 10", () => {
    render(<ProgressBar current={150} total={345} percent={43} />);
    expect(screen.getByText("Transcription: 2:30 / 5:45 (43%)")).toBeInTheDocument();
  });

  it("renders the fill bar with correct width", () => {
    const { container } = render(
      <ProgressBar current={1} total={2} percent={50} />
    );
    const fill = container.querySelector(".progress-fill");
    expect(fill).toHaveStyle({ width: "50%" });
  });
});
