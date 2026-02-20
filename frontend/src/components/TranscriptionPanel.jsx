import { useState, useRef } from "react";

const MODELS = ["tiny", "base", "small", "medium", "large", "large-v2"];
const LANGUAGES = {
  Anglais: "en",
  Francais: "fr",
  Espagnol: "es",
  Allemand: "de",
  Italien: "it",
  Japonais: "ja",
  Chinois: "zh",
};
const LANG_KEYS = Object.keys(LANGUAGES);

export default function TranscriptionPanel({ addLog, setProgress }) {
  const [files, setFiles] = useState([]);
  const [model, setModel] = useState("medium");
  const [audioLang, setAudioLang] = useState("Anglais");
  const [targetLang, setTargetLang] = useState("Francais");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const ACCEPT = ".mp4,.mp3,.wav,.m4a,.flac,.ogg,.webm";

  function handleFiles(fileList) {
    const arr = Array.from(fileList).filter((f) =>
      ACCEPT.split(",").some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    setFiles((prev) => [...prev, ...arr]);
  }

  function removeFile(index) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  async function transcribe() {
    if (files.length === 0) return;
    setLoading(true);
    setResults(null);
    setProgress({ current: 0, total: files.length, percent: 0 });

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    formData.append("model_name", model);
    formData.append("audio_lang", LANGUAGES[audioLang]);
    formData.append("target_lang", LANGUAGES[targetLang]);

    try {
      const isSingle = files.length === 1;
      const url = isSingle ? "/api/transcribe" : "/api/transcribe-batch";

      if (isSingle) {
        const singleForm = new FormData();
        singleForm.append("file", files[0]);
        singleForm.append("model_name", model);
        singleForm.append("audio_lang", LANGUAGES[audioLang]);
        singleForm.append("target_lang", LANGUAGES[targetLang]);

        const resp = await fetch(url, { method: "POST", body: singleForm });
        if (!resp.ok) throw new Error(await resp.text());
        const srt = await resp.text();
        const name = files[0].name.replace(/\.[^.]+$/, ".srt");
        setResults({ [name]: srt });
      } else {
        const resp = await fetch(url, { method: "POST", body: formData });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        setResults(data);
      }

      addLog("Transcription terminee", "green");
    } catch (err) {
      addLog(`Erreur : ${err.message}`, "red");
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
      <h2 className="panel-title">Transcription audio/video</h2>

      <div className="form-row">
        <div className="form-group">
          <label>Modele Whisper</label>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Langue de l'audio</label>
          <select value={audioLang} onChange={(e) => setAudioLang(e.target.value)}>
            {LANG_KEYS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Langue cible</label>
          <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
            {LANG_KEYS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <span className="icon">🎵</span>
        <p>Glissez vos fichiers audio/video ici ou cliquez pour parcourir</p>
        <p style={{ fontSize: "0.8rem", marginTop: 4 }}>
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
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`}>
              <span>{f.name} ({(f.size / 1024 / 1024).toFixed(1)} Mo)</span>
              <button className="remove-btn" onClick={() => removeFile(i)}>
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        className="btn btn-primary"
        disabled={files.length === 0 || loading}
        onClick={transcribe}
      >
        {loading ? "Transcription en cours..." : "Transcrire"}
      </button>

      {results && Object.entries(results).map(([name, srt]) => (
        <div key={name}>
          <div className="result-area">{srt}</div>
          <button
            className="btn btn-download"
            onClick={() => downloadSrt(name, srt)}
          >
            Telecharger {name}
          </button>
        </div>
      ))}
    </div>
  );
}
