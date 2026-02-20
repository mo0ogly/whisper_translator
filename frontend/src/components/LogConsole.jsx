import { useEffect, useRef } from "react";

export default function LogConsole({ logs, onClear }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div>
      <div className="log-header">
        <h3>Console</h3>
        <button onClick={onClear}>Effacer</button>
      </div>
      <div className="log-console">
        {logs.length === 0 && (
          <div className="log-line" style={{ color: "#555" }}>
            En attente...
          </div>
        )}
        {logs.map((log) => (
          <div
            key={log.id}
            className="log-line"
            style={{ color: log.color || "#eeeeee" }}
          >
            {log.message}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
