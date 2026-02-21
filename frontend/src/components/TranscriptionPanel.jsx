import { useState, useRef, useCallback } from "react";
import { LANGUAGES, LANG_KEYS } from "../constants";
import ProgressBar from "./ProgressBar";

const MODELS = ["tiny", "base", "small", "medium", "large", "large-v2"];
const ACCEPT = ".mp4,.mp3,.wav,.m4a,.flac,.ogg,.webm";
const ACCEPT_EXTS = ACCEPT.split(",");
const hintStyle = { fontSize: "0.8rem", marginTop: 4 };

export default function TranscriptionPanel({ addLog, setProgress, progress }) {
  const [files, setFiles] = useState([]);
  const [model, setModel] = useState("medium");
  const [audioLang, setAudioLang] = useState("English");
  const [targetLang, setTargetLang] = useState("French");
  const [transcribeOnly, setTranscribeOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [diarize, setDiarize] = useState(false);
  const [diarizing, setDiarizing] = useState(false);
  const [diarResult, setDiarResult] = useState(null);
  const [speakerNames, setSpeakerNames] = useState({});
  const inputRef = useRef(null);

  const handleFiles = useCallback((fileList) => {
    const arr = Array.from(fileList)
      .filter((f) => ACCEPT_EXTS.some((ext) => f.name.toLowerCase().endsWith(ext)))
      .map((f) => ({ file: f, id: crypto.randomUUID() }));
    setFiles((prev) => [...prev, ...arr]);
    setDiarResult(null);
    setSpeakerNames({});
  }, []);

  const removeFile = useCallback((id) => {
    setFiles((prev) => prev.filter((item) => item.id !== id));
    setDiarResult(null);
    setSpeakerNames({});
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  async function detectSpeakers() {
    if (files.length === 0) return;
    setDiarizing(true);
    setDiarResult(null);
    setSpeakerNames({});
    try {
      const fd = new FormData();
      fd.append("file", files[0].file);
      const resp = await fetch("/api/diarize", { method: "POST", body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setDiarResult(data);
      const names = {};
      data.speakers.forEach((spk, i) => { names[spk] = `Speaker ${i + 1}`; });
      setSpeakerNames(names);
      addLog(`Detected ${data.num_speakers} speaker(s)`, "green");
    } catch (err) {
      addLog(`Diarization error: ${err.message}`, "red");
    } finally {
      setDiarizing(false);
    }
  }

  async function transcribe() {
    if (files.length === 0) return;
    setLoading(true);
    setResults(null);
    setProgress({ current: 0, total: files.length, percent: 0 });

    const rawFiles = files.map((item) => item.file);
    const audioCode = LANGUAGES[audioLang];
    const targetCode = transcribeOnly ? audioCode : LANGUAGES[targetLang];

    try {
      if (diarize && diarResult) {
        // Diarized transcription path
        const fd = new FormData();
        fd.append("session_id", diarResult.session_id);
        fd.append("model_name", model);
        fd.append("audio_lang", audioCode);
        fd.append("target_lang", targetCode);
        fd.append("speaker_names", JSON.stringify(speakerNames));
        const resp = await fetch("/api/transcribe-diarized", { method: "POST", body: fd });
        if (!resp.ok) throw new Error(await resp.text());
        const srt = await resp.text();
        const name = rawFiles[0].name.replace(/\.[^.]+$/, ".srt");
        setResults({ [name]: srt });
        setDiarResult(null);
      } else {
        // Normal transcription path
        const isSingle = rawFiles.length === 1;
        const url = isSingle ? "/api/transcribe" : "/api/transcribe-batch";

        if (isSingle) {
          const singleForm = new FormData();
          singleForm.append("file", rawFiles[0]);
          singleForm.append("model_name", model);
          singleForm.append("audio_lang", audioCode);
          singleForm.append("target_lang", targetCode);
          const resp = await fetch(url, { method: "POST", body: singleForm });
          if (!resp.ok) throw new Error(await resp.text());
          const srt = await resp.text();
          const name = rawFiles[0].name.replace(/\.[^.]+$/, ".srt");
          setResults({ [name]: srt });
        } else {
          const formData = new FormData();
          rawFiles.forEach((f) => formData.append("files", f));
          formData.append("model_name", model);
          formData.append("audio_lang", audioCode);
          formData.append("target_lang", targetCode);
          const resp = await fetch(url, { method: "POST", body: formData });
          if (!resp.ok) throw new Error(await resp.text());
          const data = await resp.json();
          setResults(data);
        }
      }

      addLog("Transcription complete", "green");
    } catch (err) {
      addLog(`Error: ${err.message}`, "red");
    } finally {
      setLoading(false);
    }
  }

  function downloadSrt(filename, content) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="panel">
      <h2 className="panel-title">Audio/Video Transcription</h2>

      <div className="form-row">
        <div className="form-group">
          <label>Whisper Model</label>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Audio Language</label>
          <select value={audioLang} onChange={(e) => setAudioLang(e.target.value)}>
            {LANG_KEYS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
        {!transcribeOnly && (
          <div className="form-group">
            <label>Target Language</label>
            <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
              {LANG_KEYS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={transcribeOnly}
          onChange={(e) => setTranscribeOnly(e.target.checked)}
        />
        Transcription only (no translation)
      </label>

      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={diarize}
          onChange={(e) => {
            setDiarize(e.target.checked);
            if (!e.target.checked) { setDiarResult(null); setSpeakerNames({}); }
          }}
        />
        Enable speaker diarization (pyannote)
      </label>

      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <span className="icon">🎵</span>
        <p>Drop your audio/video files here or click to browse</p>
        <p style={hintStyle}>
          MP4, MP3, WAV, M4A, FLAC, OGG, WebM
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          style={{ display: "none" }}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="file-list">
          {files.map((item) => (
            <li key={item.id}>
              <span>{item.file.name} ({(item.file.size / 1024 / 1024).toFixed(1)} MB)</span>
              <button className="remove-btn" onClick={() => removeFile(item.id)}>
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      {diarize && files.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          {!diarResult && (
            <button
              className="btn btn-primary"
              disabled={files.length !== 1 || diarizing}
              onClick={detectSpeakers}
              style={{ marginBottom: 8 }}
            >
              {diarizing ? "Detecting speakers..." : "Detect Speakers"}
            </button>
          )}

          {files.length > 1 && (
            <p style={{ fontSize: "0.8rem", color: "#e74c3c", marginBottom: 8 }}>
              Speaker diarization only works with a single file.
            </p>
          )}

          {diarResult && (
            <div className="result-block" style={{ marginTop: 8, marginBottom: 8 }}>
              <div className="result-header">
                <span className="result-filename">
                  Detected {diarResult.num_speakers} speaker(s)
                </span>
              </div>
              <div style={{ padding: 16 }}>
                {diarResult.speakers.map((spk, i) => (
                  <div key={spk} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                    <span style={{ color: "#999", fontSize: "0.85rem", minWidth: 90 }}>
                      {spk}:
                    </span>
                    <input
                      type="text"
                      value={speakerNames[spk] || ""}
                      onChange={(e) =>
                        setSpeakerNames((prev) => ({ ...prev, [spk]: e.target.value }))
                      }
                      placeholder={`Speaker ${i + 1}`}
                      style={{
                        padding: "6px 10px",
                        background: "#1e1e1e",
                        color: "#eee",
                        border: "1px solid #3c3c3c",
                        borderRadius: 6,
                        fontSize: "0.9rem",
                        flex: 1,
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <button
        className="btn btn-primary"
        disabled={files.length === 0 || loading || (diarize && !diarResult)}
        onClick={transcribe}
      >
        {loading ? "Transcribing..." : "Transcribe"}
      </button>

      {loading && <ProgressBar {...progress} />}

      {results && Object.entries(results).map(([name, srt]) => (
        <div key={name} className="result-block">
          <div className="result-header">
            <span className="result-filename">{name}</span>
            <button
              className="btn btn-download"
              onClick={() => downloadSrt(name, srt)}
            >
              Download
            </button>
          </div>
          <pre className="result-area">{srt}</pre>
        </div>
      ))}
    </div>
  );
}
