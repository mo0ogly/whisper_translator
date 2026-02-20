import { useState, useRef } from "react";

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

export default function OllamaPanel({ addLog }) {
  const [subTab, setSubTab] = useState("srt");
  const [sourceLang, setSourceLang] = useState("Anglais");
  const [targetLang, setTargetLang] = useState("Francais");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const accept = subTab === "srt" ? ".srt" : ".txt";
  const label = subTab === "srt" ? "fichier SRT" : "fichier texte";

  function handleFile(fileList) {
    const f = fileList[0];
    if (f) setFile(f);
  }

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
      addLog("Traduction Ollama terminee", "green");
    } catch (err) {
      addLog(`Erreur Ollama : ${err.message}`, "red");
    } finally {
      setLoading(false);
    }
  }

  function download() {
    if (!result) return;
    const ext = subTab === "srt" ? ".srt" : ".txt";
    const name = file.name.replace(/\.[^.]+$/, `_traduit${ext}`);
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
      <h2 className="panel-title">Traduction via Ollama</h2>

      <div className="sub-tabs">
        <button
          className={`sub-tab-btn ${subTab === "srt" ? "active" : ""}`}
          onClick={() => { setSubTab("srt"); setFile(null); setResult(null); }}
        >
          Sous-titres SRT
        </button>
        <button
          className={`sub-tab-btn ${subTab === "text" ? "active" : ""}`}
          onClick={() => { setSubTab("text"); setFile(null); setResult(null); }}
        >
          Texte brut
        </button>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Langue source</label>
          <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
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
        <span className="icon">{subTab === "srt" ? "📝" : "📄"}</span>
        <p>Glissez votre {label} ici ou cliquez pour parcourir</p>
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
            <span>{file.name} ({(file.size / 1024).toFixed(1)} Ko)</span>
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
        {loading ? "Traduction en cours..." : "Traduire avec Ollama"}
      </button>

      {result && (
        <>
          <div className="result-area">{result}</div>
          <button className="btn btn-download" onClick={download}>
            Telecharger le resultat
          </button>
        </>
      )}
    </div>
  );
}
