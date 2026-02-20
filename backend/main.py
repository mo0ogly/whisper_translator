import os
import shutil
import tempfile
import asyncio
import traceback
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

import requests as http_requests
from faster_whisper import WhisperModel

app = FastAPI(title="Whisper Translator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────── Constantes ────────────────────

LANG_CODES = {
    "Anglais": "en",
    "Francais": "fr",
    "Espagnol": "es",
    "Allemand": "de",
    "Italien": "it",
    "Japonais": "ja",
    "Chinois": "zh",
}

SUPPORTED_EXTENSIONS = (".mp4", ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm")
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2"]
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"

# ──────────────────── WebSocket manager ─────────────

class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.connections[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self.connections.remove(ws)

manager = ConnectionManager()

async def send_log(msg: str, color: str = None):
    await manager.broadcast({"type": "log", "message": msg, "color": color})

async def send_progress(current: int, total: int):
    pct = int((current / total) * 100) if total > 0 else 0
    await manager.broadcast({
        "type": "progress",
        "current": current,
        "total": total,
        "percent": pct,
    })

# ──────────────────── Utilitaires ────────────────────

_model_cache: dict[str, WhisperModel] = {}


async def load_model(model_name: str) -> WhisperModel:
    if model_name not in _model_cache:
        _model_cache[model_name] = await asyncio.to_thread(
            WhisperModel, model_name, device="cpu", compute_type="int8"
        )
    return _model_cache[model_name]


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


async def call_ollama(text: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    target_names = {v: k for k, v in LANG_CODES.items()}
    target_name = target_names.get(target_lang, target_lang)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": (
            f"Traduis en {target_name} ce texte de sous-titre "
            f"sans modifier le style ni le decoupage :\n\n\"{text}\""
        ),
        "stream": False,
    }
    def _do():
        try:
            resp = http_requests.post(OLLAMA_URL, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json().get("response", text).strip()
        except http_requests.RequestException:
            return text
    return await asyncio.to_thread(_do)


def _transcribe_file_sync(model: WhisperModel, file_path: str, audio_code: str,
                          target_code: str) -> str:
    task = "translate" if audio_code != target_code else "transcribe"
    segments, _info = model.transcribe(
        file_path,
        task=task,
        language=audio_code,
        **({"initial_prompt": "Traduis tout en francais."}
           if target_code == "fr" and task == "translate" else {}),
    )
    srt_lines = []
    for idx, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.start)
        end = format_timestamp(seg.end)
        text = seg.text.strip()
        srt_lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(srt_lines)


async def transcribe_file(model: WhisperModel, file_path: str, audio_code: str,
                           target_code: str) -> str:
    return await asyncio.to_thread(_transcribe_file_sync, model, file_path,
                                   audio_code, target_code)


def save_upload(upload: UploadFile, dest_dir: str) -> str:
    safe_name = os.path.basename(upload.filename or "upload")
    path = os.path.join(dest_dir, safe_name)
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path

# ──────────────────── Endpoints ──────────────────────

@app.get("/api/config")
def get_config():
    return {
        "models": WHISPER_MODELS,
        "languages": LANG_CODES,
        "extensions": list(SUPPORTED_EXTENSIONS),
    }


@app.get("/api/health")
def health_check():
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ollama_ok = False
    try:
        r = http_requests.get("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {"ffmpeg": ffmpeg_ok, "ollama": ollama_ok}


@app.post("/api/transcribe")
async def transcribe_single(
    file: UploadFile = File(...),
    model_name: str = Form("medium"),
    audio_lang: str = Form("en"),
    target_lang: str = Form("fr"),
):
    if shutil.which("ffmpeg") is None:
        return PlainTextResponse("FFmpeg non detecte dans le PATH", status_code=500)

    tmp_dir = tempfile.mkdtemp()
    try:
        await send_log(f"Reception : {file.filename}")
        file_path = save_upload(file, tmp_dir)

        await send_log(f"Chargement du modele {model_name}...")
        model = await load_model(model_name)

        await send_log(f"Transcription en cours : {file.filename}")
        await send_progress(1, 1)
        srt_content = await transcribe_file(model, file_path, audio_lang, target_lang)

        await send_log(f"Transcription terminee : {file.filename}", color="green")
        return PlainTextResponse(srt_content, media_type="text/plain")
    except Exception as e:
        await send_log(f"Erreur : {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/transcribe-batch")
async def transcribe_batch(
    files: List[UploadFile] = File(...),
    model_name: str = Form("medium"),
    audio_lang: str = Form("en"),
    target_lang: str = Form("fr"),
):
    if shutil.which("ffmpeg") is None:
        return PlainTextResponse("FFmpeg non detecte dans le PATH", status_code=500)

    tmp_dir = tempfile.mkdtemp()
    try:
        valid_files = [
            f for f in files
            if f.filename.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        if not valid_files:
            await send_log("Aucun fichier audio/video valide.", color="red")
            return PlainTextResponse("Aucun fichier valide", status_code=400)

        await send_log(f"Chargement du modele {model_name}...")
        model = await load_model(model_name)

        total = len(valid_files)
        results = {}
        nb_ok = 0
        nb_errors = 0

        for index, f in enumerate(valid_files, start=1):
            await send_progress(index, total)
            await send_log(f"Traitement : {f.filename} ({index}/{total})")

            file_path = save_upload(f, tmp_dir)
            try:
                srt = await transcribe_file(model, file_path, audio_lang, target_lang)
                name = os.path.splitext(f.filename)[0]
                results[f"{name}.srt"] = srt
                await send_log(f"OK : {f.filename}", color="green")
                nb_ok += 1
            except Exception as e:
                nb_errors += 1
                await send_log(f"Erreur {f.filename} : {e}", color="red")
                traceback.print_exc()

        await send_log(
            f"Termine. {nb_ok} reussites, {nb_errors} echecs sur {total}.",
            color="cyan")
        return results
    except Exception as e:
        await send_log(f"Erreur generale : {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/ollama/translate-srt")
async def translate_srt(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("fr"),
):
    await send_log(f"Traduction SRT : {file.filename}")
    try:
        content = (await file.read()).decode("utf-8")
        lines = content.splitlines()
        output_lines = []
        bloc = []

        for line in lines:
            if line.strip() == "":
                if len(bloc) >= 3:
                    numero = bloc[0]
                    timestamp = bloc[1]
                    texte = " ".join(bloc[2:])
                    translated = await call_ollama(texte, source_lang, target_lang)
                    output_lines.append(f"{numero}\n{timestamp}\n{translated}\n")
                    await send_log(f"  Bloc {numero} traduit")
                bloc = []
            else:
                bloc.append(line)

        if len(bloc) >= 3:
            numero = bloc[0]
            timestamp = bloc[1]
            texte = " ".join(bloc[2:])
            translated = call_ollama(texte, source_lang, target_lang)
            output_lines.append(f"{numero}\n{timestamp}\n{translated}\n")

        result = "\n".join(output_lines)
        await send_log(f"Traduction terminee : {file.filename}", color="green")
        return PlainTextResponse(result, media_type="text/plain")
    except Exception as e:
        await send_log(f"Erreur : {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)


@app.post("/api/ollama/translate-text")
async def translate_text(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("fr"),
):
    await send_log(f"Traduction texte : {file.filename}")
    try:
        content = (await file.read()).decode("utf-8")
        translated = await call_ollama(content, source_lang, target_lang)
        await send_log(f"Traduction terminee : {file.filename}", color="green")
        return PlainTextResponse(translated, media_type="text/plain")
    except Exception as e:
        await send_log(f"Erreur : {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)


@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
