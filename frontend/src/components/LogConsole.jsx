import { useEffect, useRef } from "react";

const emptyStyle = { color: "#555" };

export default function LogConsole({ logs, onClear }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div>
      <div className="log-header">
        <h3>Console</h3>
        <button onClick={onClear}>Clear</button>
      </div>
      <div className="log-console">
        {logs.length === 0 && (
          <div className="log-line" style={emptyStyle}>
            Waiting...
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
