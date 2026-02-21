import { useState, useEffect, useRef, useCallback } from "react";
import TranscriptionPanel from "./components/TranscriptionPanel";
import OllamaPanel from "./components/OllamaPanel";
import LogConsole from "./components/LogConsole";
import BenchmarkModal from "./components/BenchmarkModal";

export default function App() {
  const [activeTab, setActiveTab] = useState("transcription");
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 0, percent: 0 });
  const [health, setHealth] = useState({ ffmpeg: null, ollama: null, pyannote: null });
  const [showBenchmark, setShowBenchmark] = useState(false);
  const wsRef = useRef(null);

  const addLog = useCallback((message, color = null) => {
    setLogs((prev) => [...prev, { message, color, id: Date.now() + Math.random() }]);
  }, []);

  const clearLogs = useCallback(() => setLogs([]), []);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ffmpeg: false, ollama: false, pyannote: false }));
  }, []);

  useEffect(() => {
    let cancelled = false;
    let reconnectTimeout;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          addLog(data.message, data.color);
        } else if (data.type === "progress") {
          setProgress({
            current: data.current,
            total: data.total,
            percent: data.percent,
          });
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (!cancelled) {
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };

      wsRef.current = ws;
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimeout);
      wsRef.current?.close();
    };
  }, [addLog]);

  return (
    <div className="app">
      <h1 className="app-title">
        <span>Whisper</span> Translator
      </h1>

      <div className="status-row">
        <div>
          <span className={`status-badge ${health.ffmpeg ? "ok" : "error"}`}>
            FFmpeg {health.ffmpeg ? "OK" : "missing"}
          </span>
          <span className={`status-badge ${health.ollama ? "ok" : "error"}`}>
            Ollama {health.ollama ? "OK" : "offline"}
          </span>
          <span className={`status-badge ${health.pyannote ? "ok" : "error"}`}>
            Pyannote {health.pyannote ? "OK" : "not configured"}
          </span>
        </div>
        <button
          className="tab-btn active"
          style={{ marginLeft: "auto", background: "#f59e0b", color: "#111" }}
          onClick={() => setShowBenchmark(true)}
        >
          🔍 Benchmark my PC
        </button>
      </div>

      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === "transcription" ? "active" : ""}`}
          onClick={() => setActiveTab("transcription")}
        >
          Whisper Transcription
        </button>
        <button
          className={`tab-btn ${activeTab === "ollama" ? "active" : ""}`}
          onClick={() => setActiveTab("ollama")}
        >
          Ollama Translation
        </button>
      </div>

      {activeTab === "transcription" && (
        <TranscriptionPanel addLog={addLog} setProgress={setProgress} progress={progress} />
      )}
      {activeTab === "ollama" && (
        <OllamaPanel addLog={addLog} />
      )}
      <LogConsole logs={logs} onClear={clearLogs} />

      {showBenchmark && (
        <BenchmarkModal onClose={() => setShowBenchmark(false)} />
      )}
    </div>
  );
}
