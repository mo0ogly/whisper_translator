# Whisper Translator

Application de transcription audio/video et traduction multilingue, disponible en version desktop (Tkinter) et web (React + FastAPI).

## Fonctionnalites

- **Transcription** audio/video via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MP4, MP3, WAV, M4A, FLAC, OGG, WebM)
- **Traduction de sous-titres SRT** via [Ollama](https://ollama.com/) (LLM local)
- **Traduction de texte brut** via Ollama
- **Traitement batch** de plusieurs fichiers
- **Progression temps reel** via WebSocket

## Architecture

```
whisper_translator.py        # Version desktop (Tkinter)
backend/
  main.py                    # API FastAPI + WebSocket
  requirements.txt
frontend/
  src/
    App.jsx                  # Interface React (Vite)
    components/
      TranscriptionPanel.jsx
      OllamaPanel.jsx
      LogConsole.jsx
      ProgressBar.jsx
```

## Pre-requis

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) dans le PATH
- [Ollama](https://ollama.com/) (pour la traduction)
- Node.js 18+ (pour le frontend web)

## Installation & lancement

### Version web (React + FastAPI)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (nouveau terminal)
cd frontend
npm install
npm run dev
```

Ouvrir http://localhost:5173

### Version desktop (Tkinter)

```bash
pip install faster-whisper requests
python whisper_translator.py
```

## Langues supportees

Anglais, Francais, Espagnol, Allemand, Italien, Japonais, Chinois

## Licence

MIT
