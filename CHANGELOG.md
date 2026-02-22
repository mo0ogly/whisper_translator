# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Hardware Benchmark**: Added a new `/api/benchmark` endpoint and a "Benchmark my PC" UI button to detect CPU, RAM, and GPU VRAM capabilities, providing recommendations on which Whisper models and Pyannote features the system can run smoothly.
- **M4A Auto-Conversion**: The backend now automatically converts uploaded `.m4a` files to `.wav` (16kHz, mono) before passing them to Pyannote, solving the `Format not recognised` ffmpeg errors.
- **Docker Diarization Support**: Added the `HF_TOKEN` environment variable pipeline to `docker-compose.yml` to allow the Pyannote model to be downloaded inside the Docker container.

### Fixed
- **Pyannote NoneType Crash**: Added explicit `ValueError` handling in `backend/main.py` to catch when the Pyannote pipeline fails to initialize (e.g., due to missing HuggingFace license acceptance) instead of throwing obscure `NoneType` errors later during the pipeline run.
- **Pyannote Numpy Conflict**: Pinned `numpy<2.0` in `requirements.txt` to fix a `AttributeError: module 'numpy' has no attribute 'NAN'` crash that occurs with `pyannote-audio v3.1` running on numpy 2+.
- **Diarization Frontend State**: Fixed an issue where the frontend dropped the speaker diarization object before the user could click "Transcribe", preventing the `.srt` generation.

### Changed
- **Documentation**: Substantially updated the `README.md` to emphasize local hardware constraints (VRAM requirements for Diarization), explicitly detail the one-time HuggingFace license acceptance step, and clarify secure token usage via `.env`.
