"""Unit tests for the Whisper Translator API."""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Patch WhisperModel before importing app (module loads at import time)
with patch("backend.main.WhisperModel"):
    from backend.main import (
        app,
        format_timestamp,
        save_upload,
        _transcribe_file_sync,
        LANG_CODES,
        SUPPORTED_EXTENSIONS,
        WHISPER_MODELS,
    )

client = TestClient(app)


# ──────────────────── format_timestamp ────────────────────

class TestFormatTimestamp:
    def test_zero(self):
        assert format_timestamp(0.0) == "00:00:00,000"

    def test_seconds_only(self):
        assert format_timestamp(5.123) == "00:00:05,123"

    def test_minutes(self):
        assert format_timestamp(65.5) == "00:01:05,500"

    def test_hours(self):
        assert format_timestamp(3661.999) == "01:01:01,999"

    def test_large_value(self):
        result = format_timestamp(7200.0)
        assert result == "02:00:00,000"


# ──────────────────── save_upload (path traversal) ────────

class TestSaveUpload:
    def test_basename_strips_path_traversal(self, tmp_path):
        mock_upload = MagicMock()
        mock_upload.filename = "../../etc/passwd"
        mock_upload.file.read.side_effect = [b"test", b""]

        path = save_upload(mock_upload, str(tmp_path))
        assert os.path.basename(path) == "passwd"
        assert str(tmp_path) in path

    def test_normal_filename(self, tmp_path):
        mock_upload = MagicMock()
        mock_upload.filename = "audio.mp3"
        mock_upload.file.read.side_effect = [b"test", b""]

        path = save_upload(mock_upload, str(tmp_path))
        assert path.endswith("audio.mp3")

    def test_none_filename(self, tmp_path):
        mock_upload = MagicMock()
        mock_upload.filename = None
        mock_upload.file.read.side_effect = [b"test", b""]

        path = save_upload(mock_upload, str(tmp_path))
        assert os.path.basename(path) == "upload"


# ──────────────────── GET /api/config ─────────────────────

class TestConfigEndpoint:
    def test_returns_models(self):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["models"] == WHISPER_MODELS

    def test_returns_languages(self):
        resp = client.get("/api/config")
        data = resp.json()
        assert data["languages"] == LANG_CODES

    def test_returns_extensions(self):
        resp = client.get("/api/config")
        data = resp.json()
        assert set(data["extensions"]) == set(SUPPORTED_EXTENSIONS)


# ──────────────────── GET /api/health ─────────────────────

class TestHealthEndpoint:
    @patch("backend.main.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("backend.main.http_requests.get")
    def test_all_ok(self, mock_get, mock_which):
        mock_get.return_value = MagicMock(status_code=200)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ffmpeg"] is True
        assert data["ollama"] is True

    @patch("backend.main.shutil.which", return_value=None)
    @patch("backend.main.http_requests.get", side_effect=ConnectionError)
    def test_all_down(self, mock_get, mock_which):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["ffmpeg"] is False
        assert data["ollama"] is False


# ──────────────────── POST /api/transcribe ────────────────

class TestTranscribeEndpoint:
    @patch("backend.main.shutil.which", return_value=None)
    def test_no_ffmpeg_returns_500(self, mock_which):
        resp = client.post(
            "/api/transcribe",
            files={"file": ("test.mp3", b"fake", "audio/mpeg")},
            data={"model_name": "tiny", "audio_lang": "en", "target_lang": "fr"},
        )
        assert resp.status_code == 500
        assert "FFmpeg" in resp.text


# ──────────────────── POST /api/transcribe-batch ──────────

class TestTranscribeBatchEndpoint:
    @patch("backend.main.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_no_valid_files_returns_400(self, mock_which):
        resp = client.post(
            "/api/transcribe-batch",
            files={"files": ("readme.txt", b"not audio", "text/plain")},
            data={"model_name": "tiny", "audio_lang": "en", "target_lang": "fr"},
        )
        assert resp.status_code == 400


# ──────────────────── _transcribe_file_sync ───────────────

class TestTranscribeFileSync:
    def test_transcribe_mode(self):
        mock_model = MagicMock()
        seg = MagicMock(start=0.0, end=1.5, text=" Hello ")
        mock_model.transcribe.return_value = (iter([seg]), None)

        result = _transcribe_file_sync(mock_model, "fake.mp3", "en", "en")
        assert "Hello" in result
        assert "00:00:00,000 --> 00:00:01,500" in result
        mock_model.transcribe.assert_called_once()
        assert mock_model.transcribe.call_args[1]["task"] == "transcribe"

    def test_translate_mode(self):
        mock_model = MagicMock()
        seg = MagicMock(start=0.0, end=2.0, text=" Bonjour ")
        mock_model.transcribe.return_value = (iter([seg]), None)

        result = _transcribe_file_sync(mock_model, "fake.mp3", "en", "fr")
        assert "Bonjour" in result
        assert mock_model.transcribe.call_args[1]["task"] == "translate"


# ──────────────────── Constants ───────────────────────────

class TestConstants:
    def test_lang_codes_not_empty(self):
        assert len(LANG_CODES) >= 7

    def test_supported_extensions(self):
        assert ".mp4" in SUPPORTED_EXTENSIONS
        assert ".mp3" in SUPPORTED_EXTENSIONS

    def test_whisper_models(self):
        assert "tiny" in WHISPER_MODELS
        assert "medium" in WHISPER_MODELS
