import os
import json as _json
import shutil
import tempfile
import asyncio
import traceback
import time
import uuid
import subprocess
import psutil
from typing import List

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

import requests as http_requests
from faster_whisper import WhisperModel

app = FastAPI(title="Whisper Translator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────── Constants ──────────────────────

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
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# ──────────────────── WebSocket Manager ──────────────

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

# ──────────────────── Utilities ──────────────────────

_model_cache: dict[str, WhisperModel] = {}


def _detect_device():
    """Auto-detect CUDA GPU, fallback to CPU."""
    try:
        import ctranslate2
        if "cuda" in ctranslate2.get_supported_compute_types("cuda"):
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


DEVICE, COMPUTE_TYPE = _detect_device()


async def load_model(model_name: str) -> WhisperModel:
    if model_name not in _model_cache:
        await send_log(f"Loading {model_name} on {DEVICE} ({COMPUTE_TYPE})...")
        _model_cache[model_name] = await asyncio.to_thread(
            WhisperModel, model_name, device=DEVICE, compute_type=COMPUTE_TYPE
        )
    return _model_cache[model_name]


def format_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    h = total_ms // 3_600_000
    total_ms %= 3_600_000
    m = total_ms // 60_000
    total_ms %= 60_000
    s = total_ms // 1000
    ms = total_ms % 1000
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
                          target_code: str, progress_queue=None) -> str:
    task = "translate" if audio_code != target_code else "transcribe"
    segments, info = model.transcribe(
        file_path,
        task=task,
        language=audio_code,
        beam_size=1,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    duration = info.duration if info and hasattr(info, "duration") else 0
    srt_lines = []
    for idx, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.start)
        end = format_timestamp(seg.end)
        text = seg.text.strip()
        srt_lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
        if progress_queue is not None and duration > 0:
            progress_queue.put_nowait({
                "current": round(seg.end, 1),
                "total": round(duration, 1),
                "percent": min(int((seg.end / duration) * 100), 99),
                "segment_text": text,
            })
    return "\n".join(srt_lines)


async def transcribe_file(model: WhisperModel, file_path: str, audio_code: str,
                           target_code: str) -> str:
    import queue
    progress_queue = queue.Queue()

    async def _poll_progress():
        while True:
            try:
                msg = progress_queue.get_nowait()
                await send_progress(msg["current"], msg["total"])
                await send_log(
                    f"  [{format_timestamp(msg['current'])}] {msg['segment_text']}",
                )
            except queue.Empty:
                pass
            await asyncio.sleep(0.3)

    poll_task = asyncio.create_task(_poll_progress())
    try:
        result = await asyncio.to_thread(
            _transcribe_file_sync, model, file_path, audio_code, target_code,
            progress_queue,
        )
    finally:
        poll_task.cancel()
        # Flush remaining messages
        while not progress_queue.empty():
            msg = progress_queue.get_nowait()
            await send_progress(msg["current"], msg["total"])
    return result


def save_upload(upload: UploadFile, dest_dir: str) -> str:
    safe_name = os.path.basename(upload.filename or "upload")
    path = os.path.join(dest_dir, safe_name)
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path


# ──────────────────── Diarization ─────────────────────

_diarization_cache: dict[str, dict] = {}
_diarization_pipeline = None
DIARIZATION_TTL = 3600  # 1 hour


def _cleanup_expired_sessions():
    now = time.time()
    expired = [
        sid for sid, data in _diarization_cache.items()
        if now - data["created_at"] > DIARIZATION_TTL
    ]
    for sid in expired:
        shutil.rmtree(_diarization_cache[sid].get("tmp_dir", ""), ignore_errors=True)
        del _diarization_cache[sid]


def _load_diarization_pipeline():
    """Load pyannote pipeline (blocking). Called via asyncio.to_thread."""
    global _diarization_pipeline
    if _diarization_pipeline is not None:
        return _diarization_pipeline

    from pyannote.audio import Pipeline

    if not HF_TOKEN:
        raise ValueError(
            "HF_TOKEN environment variable is required for speaker diarization. "
            "Get a token at https://huggingface.co/settings/tokens"
        )

    _diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=HF_TOKEN,
    )
    
    if _diarization_pipeline is None:
        raise ValueError(
            "HuggingFace token works, but you MUST accept the Pyannote license online first. "
            "Please visit https://hf.co/pyannote/speaker-diarization-3.1 and "
            "https://hf.co/pyannote/segmentation-3.0 to accept the conditions."
        )

    if DEVICE == "cuda":
        import torch
        _diarization_pipeline.to(torch.device("cuda"))

    return _diarization_pipeline


def _run_diarization_sync(pipeline, file_path: str):
    """Run pyannote diarization. Returns (unique_speakers, segments)."""
    diarization = pipeline(file_path)
    segments = []
    speakers_set = set()
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append((turn.start, turn.end, speaker))
        speakers_set.add(speaker)
    return sorted(speakers_set), segments


def _find_speaker(seg_start, seg_end, diar_segments, speaker_names):
    """Find pyannote speaker with maximum time overlap for a Whisper segment."""
    overlap_by_speaker = {}
    for d_start, d_end, d_speaker in diar_segments:
        overlap = max(0.0, min(seg_end, d_end) - max(seg_start, d_start))
        if overlap > 0:
            overlap_by_speaker[d_speaker] = overlap_by_speaker.get(d_speaker, 0.0) + overlap
    if not overlap_by_speaker:
        return "Unknown"
    best = max(overlap_by_speaker, key=overlap_by_speaker.get)
    return speaker_names.get(best, best)


def _transcribe_segments_sync(model: WhisperModel, file_path: str,
                               audio_code: str, target_code: str) -> list[dict]:
    """Like _transcribe_file_sync but returns raw segment dicts."""
    task = "translate" if audio_code != target_code else "transcribe"
    segments, _info = model.transcribe(
        file_path, task=task, language=audio_code,
        beam_size=1, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]


def _build_srt_with_speakers(segments, diar_segments, speaker_names):
    """Build SRT with [Speaker Name]: prefix."""
    srt_lines = []
    for idx, seg in enumerate(segments, start=1):
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        speaker = _find_speaker(seg["start"], seg["end"], diar_segments, speaker_names)
        srt_lines.append(f"{idx}\n{start} --> {end}\n[{speaker}]: {seg['text']}\n")
    return "\n".join(srt_lines)


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
    pyannote_ok = False
    try:
        import pyannote.audio  # noqa: F401
        pyannote_ok = bool(HF_TOKEN)
    except ImportError:
        pass

    return {"ffmpeg": ffmpeg_ok, "ollama": ollama_ok, "pyannote": pyannote_ok}


@app.post("/api/transcribe")
async def transcribe_single(
    file: UploadFile = File(...),
    model_name: str = Form("medium"),
    audio_lang: str = Form("en"),
    target_lang: str = Form("fr"),
):
    if shutil.which("ffmpeg") is None:
        return PlainTextResponse("FFmpeg not found in PATH", status_code=500)

    tmp_dir = tempfile.mkdtemp()
    try:
        await send_log(f"Received: {file.filename}")
        file_path = save_upload(file, tmp_dir)

        await send_log(f"Loading model {model_name}...")
        model = await load_model(model_name)

        await send_log(f"Transcribing: {file.filename}")
        await send_progress(0, 1)
        srt_content = await transcribe_file(model, file_path, audio_lang, target_lang)
        await send_progress(1, 1)

        await send_log(f"Transcription complete: {file.filename}", color="green")
        return PlainTextResponse(srt_content, media_type="text/plain")
    except Exception as e:
        await send_log(f"Error: {e}", color="red")
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
        return PlainTextResponse("FFmpeg not found in PATH", status_code=500)

    tmp_dir = tempfile.mkdtemp()
    try:
        valid_files = [
            f for f in files
            if f.filename.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        if not valid_files:
            await send_log("No valid audio/video files.", color="red")
            return PlainTextResponse("No valid files", status_code=400)

        await send_log(f"Loading model {model_name}...")
        model = await load_model(model_name)

        total = len(valid_files)
        results = {}
        nb_ok = 0
        nb_errors = 0

        for index, f in enumerate(valid_files, start=1):
            await send_progress(index, total)
            await send_log(f"Processing: {f.filename} ({index}/{total})")

            file_path = save_upload(f, tmp_dir)
            try:
                srt = await transcribe_file(model, file_path, audio_lang, target_lang)
                name = os.path.splitext(f.filename)[0]
                results[f"{name}.srt"] = srt
                await send_log(f"OK : {f.filename}", color="green")
                nb_ok += 1
            except Exception as e:
                nb_errors += 1
                await send_log(f"Error {f.filename}: {e}", color="red")
                traceback.print_exc()

        await send_log(
            f"Done. {nb_ok} succeeded, {nb_errors} failed out of {total}.",
            color="cyan")
        return results
    except Exception as e:
        await send_log(f"General error: {e}", color="red")
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
    await send_log(f"SRT translation: {file.filename}")
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
                    await send_log(f"  Block {numero} translated")
                bloc = []
            else:
                bloc.append(line)

        if len(bloc) >= 3:
            numero = bloc[0]
            timestamp = bloc[1]
            texte = " ".join(bloc[2:])
            translated = await call_ollama(texte, source_lang, target_lang)
            output_lines.append(f"{numero}\n{timestamp}\n{translated}\n")

        result = "\n".join(output_lines)
        await send_log(f"Translation complete: {file.filename}", color="green")
        return PlainTextResponse(result, media_type="text/plain")
    except Exception as e:
        await send_log(f"Error: {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)


@app.post("/api/ollama/translate-text")
async def translate_text(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("fr"),
):
    await send_log(f"Text translation: {file.filename}")
    try:
        content = (await file.read()).decode("utf-8")
        translated = await call_ollama(content, source_lang, target_lang)
        await send_log(f"Translation complete: {file.filename}", color="green")
        return PlainTextResponse(translated, media_type="text/plain")
    except Exception as e:
        await send_log(f"Error: {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)


@app.post("/api/diarize")
async def diarize_file(
    file: UploadFile = File(...),
):
    """Phase 1: Run speaker diarization and cache results."""
    if not HF_TOKEN:
        return PlainTextResponse(
            "HF_TOKEN not configured. Set the HF_TOKEN environment variable.",
            status_code=500,
        )

    _cleanup_expired_sessions()
    tmp_dir = tempfile.mkdtemp()
    try:
        await send_log(f"Diarization: received {file.filename}")
        file_path = save_upload(file, tmp_dir)
        
        # Convert to WAV for pyannote compatibility (handles m4a, etc)
        wav_path = os.path.join(tmp_dir, "converted.wav")
        try:
            await send_log(f"Converting audio to WAV for Pyannote...")
            cmd = ["ffmpeg", "-y", "-i", file_path, "-ac", "1", "-ar", "16000", wav_path]
            await asyncio.to_thread(subprocess.run, cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            diarize_path = wav_path
        except Exception as e:
            await send_log(f"Warning: ffmpeg conversion failed, trying original file. Error: {e}", color="yellow")
            diarize_path = file_path

        await send_log("Loading pyannote diarization pipeline...")
        pipeline = await asyncio.to_thread(_load_diarization_pipeline)

        await send_log(f"Running speaker detection on {file.filename}...")
        speakers, segments = await asyncio.to_thread(
            _run_diarization_sync, pipeline, diarize_path
        )

        session_id = str(uuid.uuid4())
        _diarization_cache[session_id] = {
            "file_path": file_path,
            "tmp_dir": tmp_dir,
            "speakers": speakers,
            "segments": segments,
            "filename": file.filename,
            "created_at": time.time(),
        }

        await send_log(
            f"Diarization complete: {len(speakers)} speaker(s) detected",
            color="green",
        )
        return {
            "session_id": session_id,
            "num_speakers": len(speakers),
            "speakers": speakers,
        }
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        await send_log(f"Diarization error: {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)


@app.post("/api/transcribe-diarized")
async def transcribe_diarized(
    session_id: str = Form(...),
    model_name: str = Form("medium"),
    audio_lang: str = Form("en"),
    target_lang: str = Form("fr"),
    speaker_names: str = Form("{}"),
):
    """Phase 2: Transcribe with Whisper and merge with cached diarization."""
    session = _diarization_cache.get(session_id)
    if not session:
        return PlainTextResponse(
            "Diarization session expired or not found. Please re-upload.",
            status_code=404,
        )

    try:
        names_map = _json.loads(speaker_names)
    except _json.JSONDecodeError:
        return PlainTextResponse("Invalid speaker_names JSON", status_code=400)

    file_path = session["file_path"]
    diar_segments = session["segments"]
    filename = session.get("filename", "file")

    try:
        await send_log(f"Loading model {model_name}...")
        model = await load_model(model_name)

        await send_log(f"Transcribing with diarization: {filename}")
        await send_progress(1, 1)

        whisper_segments = await asyncio.to_thread(
            _transcribe_segments_sync, model, file_path, audio_lang, target_lang,
        )

        srt_content = _build_srt_with_speakers(
            whisper_segments, diar_segments, names_map
        )

        await send_log(f"Diarized transcription complete: {filename}", color="green")
        return PlainTextResponse(srt_content, media_type="text/plain")
    except Exception as e:
        await send_log(f"Error: {e}", color="red")
        traceback.print_exc()
        return PlainTextResponse(str(e), status_code=500)
    finally:
        if session_id in _diarization_cache:
            shutil.rmtree(session.get("tmp_dir", ""), ignore_errors=True)
            del _diarization_cache[session_id]


@app.get("/api/benchmark")
async def benchmark_system():
    # RAM
    ram = psutil.virtual_memory()
    total_ram_gb = ram.total / (1024**3)
    
    # GPU
    gpu_name = "None"
    gpu_vram_gb = 0
    has_gpu = False
    
    if DEVICE == "cuda":
        try:
            import torch
            has_gpu = True
            gpu_name = torch.cuda.get_device_name(0)
            gpu_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        except Exception:
            gpu_name = "Unknown CUDA Device"

    # CPU
    cpu_cores = psutil.cpu_count(logical=True)
    
    # Recommendations
    whisper_base_ok = True
    whisper_large_ok = has_gpu and gpu_vram_gb >= 6 or (not has_gpu and total_ram_gb >= 16)
    diarization_ok = has_gpu and gpu_vram_gb >= 4
    diarization_warning = "Slow but usable (CPU mode)" if not diarization_ok and total_ram_gb >= 8 else "Not recommended (will likely crash or take hours)" if not diarization_ok else "Good"

    return {
        "hardware": {
            "ram_gb": round(total_ram_gb, 1),
            "cpu_cores": cpu_cores,
            "gpu": gpu_name,
            "gpu_vram_gb": round(gpu_vram_gb, 1) if has_gpu else 0,
            "compute_type": COMPUTE_TYPE
        },
        "recommendations": {
            "whisper_base": "Good",
            "whisper_large": "Good" if whisper_large_ok else "Slow (Not enough RAM/VRAM)",
            "diarization": "Good" if diarization_ok else diarization_warning
        }
    }


@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# ──────────────────── Static files (production) ──────

STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
