import { useState, useEffect, useRef, useCallback } from "react";
import TranscriptionPanel from "./components/TranscriptionPanel";
import OllamaPanel from "./components/OllamaPanel";
import LogConsole from "./components/LogConsole";
import ProgressBar from "./components/ProgressBar";

export default function App() {
  const [activeTab, setActiveTab] = useState("transcription");
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 0, percent: 0 });
  const [health, setHealth] = useState({ ffmpeg: null, ollama: null });
  const wsRef = useRef(null);

  const addLog = useCallback((message, color = null) => {
    setLogs((prev) => [...prev, { message, color, id: Date.now() + Math.random() }]);
  }, []);

  const clearLogs = useCallback(() => setLogs([]), []);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ffmpeg: false, ollama: false }));
  }, []);

  useEffect(() => {
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
      setTimeout(() => {
        wsRef.current = null;
      }, 3000);
    };

    wsRef.current = ws;
    return () => ws.close();
  }, [addLog]);

  return (
    <div className="app">
      <h1 className="app-title">
        <span>Whisper</span> Translator
      </h1>

      <div className="status-row">
        <span className={`status-badge ${health.ffmpeg ? "ok" : "error"}`}>
          FFmpeg {health.ffmpeg ? "OK" : "manquant"}
        </span>
        <span className={`status-badge ${health.ollama ? "ok" : "error"}`}>
          Ollama {health.ollama ? "OK" : "hors ligne"}
        </span>
      </div>

      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === "transcription" ? "active" : ""}`}
          onClick={() => setActiveTab("transcription")}
        >
          Transcription Whisper
        </button>
        <button
          className={`tab-btn ${activeTab === "ollama" ? "active" : ""}`}
          onClick={() => setActiveTab("ollama")}
        >
          Traduction Ollama
        </button>
      </div>

      {activeTab === "transcription" && (
        <TranscriptionPanel addLog={addLog} setProgress={setProgress} />
      )}
      {activeTab === "ollama" && (
        <OllamaPanel addLog={addLog} />
      )}

      <ProgressBar {...progress} />
      <LogConsole logs={logs} onClear={clearLogs} />
    </div>
  );
}
