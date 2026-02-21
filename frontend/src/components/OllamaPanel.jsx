import { useState, useRef, useCallback } from "react";
import { LANGUAGES, LANG_KEYS } from "../constants";

export default function OllamaPanel({ addLog }) {
  const [subTab, setSubTab] = useState("srt");
  const [sourceLang, setSourceLang] = useState("English");
  const [targetLang, setTargetLang] = useState("French");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const accept = subTab === "srt" ? ".srt" : ".txt";
  const label = subTab === "srt" ? "SRT file" : "text file";

  function handleFile(fileList) {
    const f = fileList[0];
    if (f) setFile(f);
  }

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const switchToSrt = useCallback(() => {
    setSubTab("srt"); setFile(null); setResult(null);
  }, []);

  const switchToText = useCallback(() => {
    setSubTab("text"); setFile(null); setResult(null);
  }, []);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files);
  }

  async function translate() {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_lang", LANGUAGES[sourceLang]);
    formData.append("target_lang", LANGUAGES[targetLang]);

    const url =
      subTab === "srt"
        ? "/api/ollama/translate-srt"
        : "/api/ollama/translate-text";

    try {
      const resp = await fetch(url, { method: "POST", body: formData });
      if (!resp.ok) throw new Error(await resp.text());
      const text = await resp.text();
      setResult(text);
      addLog("Ollama translation complete", "green");
    } catch (err) {
      addLog(`Ollama error: ${err.message}`, "red");
    } finally {
      setLoading(false);
    }
  }

  function download() {
    if (!result) return;
    const ext = subTab === "srt" ? ".srt" : ".txt";
    const name = file.name.replace(/\.[^.]+$/, `_translated${ext}`);
    const blob = new Blob([result], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="panel">
      <h2 className="panel-title">Ollama Translation</h2>

      <div className="sub-tabs">
        <button
          className={`sub-tab-btn ${subTab === "srt" ? "active" : ""}`}
          onClick={switchToSrt}
        >
          SRT Subtitles
        </button>
        <button
          className={`sub-tab-btn ${subTab === "text" ? "active" : ""}`}
          onClick={switchToText}
        >
          Plain Text
        </button>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Source Language</label>
          <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
            {LANG_KEYS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Target Language</label>
          <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
            {LANG_KEYS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <span className="icon">{subTab === "srt" ? "📝" : "📄"}</span>
        <p>Drop your {label} here or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files)}
        />
      </div>

      {file && (
        <ul className="file-list">
          <li>
            <span>{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
            <button className="remove-btn" onClick={() => setFile(null)}>
              ✕
            </button>
          </li>
        </ul>
      )}

      <button
        className="btn btn-purple"
        disabled={!file || loading}
        onClick={translate}
      >
        {loading ? "Translating..." : "Translate with Ollama"}
      </button>

      {result && (
        <div className="result-block">
          <div className="result-header">
            <span className="result-filename">Translation Result</span>
            <button className="btn btn-download" onClick={download}>
              Download
            </button>
          </div>
          <pre className="result-area">{result}</pre>
        </div>
      )}
    </div>
  );
}
