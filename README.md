# Whisper Translator

Audio/video transcription and multilingual translation app, available as a desktop version (Tkinter) and a web app (React + FastAPI).

> ⚠️ **100% LOCAL & PRIVATE:** This application runs entirely on your own hardware. No audio or text is ever sent to the cloud. **However**, this means performance is strictly tied to your machine's capabilities (especially your Graphics Card / VRAM).

## Features

- **Transcription** of audio/video files via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MP4, MP3, WAV, M4A, FLAC, OGG, WebM)
- **Transcription-only mode** (no translation) with a single checkbox
- **SRT subtitle translation** via [Ollama](https://ollama.com/) (local LLM)
- **Plain text translation** via Ollama
- **Batch processing** of multiple files at once
- **Real-time progress** via WebSocket
- **Auto-reconnecting** WebSocket connection
- **GPU auto-detection** (CUDA) with CPU fallback
- **VAD filtering** to skip silence and speed up transcription
- **Speaker diarization** via [pyannote.audio](https://github.com/pyannote/pyannote-audio) -- detect speakers, assign names, get labeled SRT

## Architecture

```text
whisper_translator.py        # Desktop version (Tkinter)
backend/
  main.py                    # FastAPI + WebSocket API
  requirements.txt
  tests/                     # Unit tests (pytest)
frontend/
  src/
    App.jsx                  # React UI (Vite)
    constants.js             # Shared constants (languages)
    test/
      setup.js               # Vitest config
    components/
      TranscriptionPanel.jsx
      OllamaPanel.jsx
      LogConsole.jsx
      ProgressBar.jsx
      *.test.jsx             # Unit tests (Vitest)
Dockerfile                   # Multi-stage build
docker-compose.yml
Makefile
start.sh                     # Quick-start script
```

## Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) in your PATH
- [Ollama](https://ollama.com/) (for translation features)
- Node.js 18+ (for the web frontend)
- (Optional) [HuggingFace token](https://huggingface.co/settings/tokens) for speaker diarization

## Quick Start

### Start script (easiest)

```bash
chmod +x start.sh
./start.sh
```

Launches backend and frontend in parallel. Open <http://localhost:5173>.

### Makefile

```bash
make install       # Install all dependencies
make dev-backend   # Terminal 1
make dev-frontend  # Terminal 2
```

Available commands:

| Command | Description |
| ------- | ----------- |
| `make install` | Install Python + Node dependencies |
| `make dev-backend` | Start FastAPI (port 8000) |
| `make dev-frontend` | Start Vite (port 5173) |
| `make build` | Build frontend for production |
| `make test` | Run backend unit tests |
| `make docker` | Build Docker image |
| `make docker-up` | Start via docker compose |
| `make docker-down` | Stop docker compose |
| `make clean` | Remove build artifacts |

### Docker

```bash
# Build + start
docker compose up -d

# Or manually
docker build -t whisper-translator .
docker run -p 8000:8000 whisper-translator
```

Open <http://localhost:8000>. The frontend is served directly by FastAPI.

Ollama must be running on the host machine. The container connects via `host.docker.internal:11434`.

### Manual installation

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

### Desktop version (Tkinter)

```bash
pip install faster-whisper requests
python whisper_translator.py
```

## User Guide

### Whisper Transcription tab

This tab lets you transcribe audio/video files into SRT subtitles.

1. **Select a Whisper model** from the dropdown. Available models, from fastest to most accurate:
   - `tiny` / `base` / `small` -- fast, lower accuracy
   - `medium` -- good balance (default)
   - `large` / `large-v2` -- best accuracy, slower

2. **Choose the audio language** -- the language spoken in your file.

3. **Choose the target language** -- the language for the output subtitles. If it differs from the audio language, Whisper will translate during transcription.

4. **Transcription-only mode** -- check "Transcription only (no translation)" to produce subtitles in the same language as the audio, without any translation.

5. **Add files** -- drag and drop audio/video files onto the drop zone, or click to browse. Accepted formats: MP4, MP3, WAV, M4A, FLAC, OGG, WebM. You can add multiple files for batch processing.

6. **Click "Transcribe"** -- progress and logs appear in real time. When complete, the SRT result is displayed with the filename and a download button.

### Speaker Diarization

Identify who speaks when in a recording and label each subtitle line with the speaker's name.

> 🚨 **HARDWARE WARNING:** Pyannote Diarization is an extremely heavy machine learning process. **It is highly recommended to have an NVIDIA GPU with at least 4GB of VRAM.** Running diarization on a CPU or low-end GPU may take **hours** for a long video or even crash due to out-of-memory errors. **Use the "Benchmark my PC" button** in the UI to assess your system.

**Setup (one-time manual step required):**

You *must* manually accept the Pyannote license terms on their website for the model to download. `start.sh` cannot do this for you.

1. Create a free account on [HuggingFace](https://huggingface.co/)
2. ⚠️ **MANDATORY:** You must visit **BOTH** links below, log in, and click the **"Agree and access repository"** button on each page:
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
3. Create an Access Token at [HuggingFace Settings -> Access Tokens](https://huggingface.co/settings/tokens). It only needs "Read" permissions.
4. **Set the token safely:** Create a file named `.env` in the `backend/` folder and paste your token inside. 
   
   *Note: This file is ignored by Git (`.gitignore`), so your token will remain private on your machine and will never be published to GitHub.*

```text
# backend/.env
HF_TOKEN="hf_your_token_here"
```

The status badge at the top of the app will show "Pyannote OK" when properly configured.

**Usage:**

1. In the Whisper Transcription tab, check **"Enable speaker diarization (pyannote)"**
2. Add a single audio file (diarization works on one file at a time)
3. Click **"Detect Speakers"** -- the backend analyzes the audio and returns the number of speakers detected
4. Assign names to each speaker in the text fields (defaults: Speaker 1, Speaker 2...)
5. Click **"Transcribe"** -- the output SRT contains speaker labels:

```text
1
00:00:00,000 --> 00:00:02,500
[Alice]: Hello, how are you?

2
00:00:02,800 --> 00:00:04,100
[Bob]: I'm doing great, thanks!
```

### Ollama Translation tab

This tab lets you translate existing SRT subtitle files or plain text files using a local Ollama LLM.

1. **Choose a sub-tab**:
   - **SRT Subtitles** -- translates an `.srt` file block by block, preserving timestamps
   - **Plain Text** -- translates an entire text file

2. **Select source and target languages**.

3. **Drop or browse** for your `.srt` or `.txt` file.

4. **Click "Translate with Ollama"** -- each block is sent to the LLM. The translated result appears with a download button.

> **Note:** Ollama must be running locally. The status badge at the top shows "Ollama OK" when connected, or "Ollama offline" otherwise.

### Console

The console at the bottom displays real-time logs from the backend: model loading, file processing, errors, and completion status. Click **Clear** to reset.

### Performance tips

- **Check your System:** Click the **"Benchmark my PC"** button in the top-right corner of the app to get a realistic assessment of what your hardware can do.
- **Use a GPU** -- if you have an NVIDIA GPU with CUDA, the backend auto-detects it and uses `float16` for much faster transcription.
- **Use a smaller model** -- `tiny` or `base` are significantly faster than `large-v2` and can run on CPUs and low-end GPUs.
- **VAD filtering** is enabled by default, skipping silence to speed up processing.
- On CPU, expect ~1x real-time for `medium` model. GPU can be 5-10x faster.

## Environment Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama API endpoint |
| `OLLAMA_MODEL` | `mistral` | LLM model for translation |
| `HF_TOKEN` | (none) | HuggingFace token for speaker diarization |

## Tests

### Backend (pytest)

```bash
make test
# or
cd backend && python -m pytest tests/ -v
```

### Frontend (Vitest + React Testing Library)

```bash
cd frontend
npm test          # Watch mode (auto-rerun)
npm run test:run  # Single run
```

**38 tests** cover all React components:

| File | Coverage |
| ---- | -------- |
| `ProgressBar.test.jsx` | Conditional rendering, percentage, progress bar fill |
| `LogConsole.test.jsx` | Empty state, messages, colors, clear button |
| `TranscriptionPanel.test.jsx` | Models, languages, file selection/removal, drag & drop, speaker diarization |
| `OllamaPanel.test.jsx` | SRT/Text sub-tabs, languages, drop zone |
| `App.test.jsx` | Tab navigation, health check (FFmpeg, Ollama, Pyannote), error status, console |

## Supported Languages

English, French, Spanish, German, Italian, Japanese, Chinese

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT -- see [LICENSE](LICENSE).
