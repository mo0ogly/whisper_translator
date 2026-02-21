function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function ProgressBar({ current, total, percent }) {
  if (total === 0) return null;

  const isTimeBased = total > 10;
  const label = isTimeBased
    ? `Transcription: ${formatTime(current)} / ${formatTime(total)} (${percent}%)`
    : `File ${current} of ${total} (${percent}%)`;

  return (
    <div className="progress-container">
      <div className="progress-label">{label}</div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
