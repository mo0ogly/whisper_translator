export default function ProgressBar({ current, total, percent }) {
  if (total === 0) return null;

  return (
    <div className="progress-container">
      <div className="progress-label">
        Fichier {current} sur {total} ({percent}%)
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
