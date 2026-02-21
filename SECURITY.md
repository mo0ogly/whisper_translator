# Security

## Implemented measures

- **Path traversal**: `save_upload()` uses `os.path.basename()` to sanitize malicious filenames (`../../etc/passwd`)
- **Temporary files**: uploads are stored in `tempfile.mkdtemp()` and cleaned up in a `finally` block
- **No command injection**: no `subprocess` calls with user input. Ollama is called via `requests.post(json=...)`, not shell `curl`
- **Non-blocking I/O**: `asyncio.to_thread()` prevents CPU-intensive calls (Whisper, Ollama) from freezing the event loop and WebSocket
- **Extension validation**: only audio/video files with known extensions are accepted

## Points of attention

- **CORS**: `allow_origins=["*"]` is configured for development. Restrict to allowed domains in production
- **Ollama**: the local API has no authentication. Do not expose port 11434 publicly
- **Upload size**: no explicit file size limit. Add a limit via nginx/reverse-proxy in production
- **HTTPS**: use a reverse proxy (nginx, Caddy) with TLS in production

## Reporting a vulnerability

Open a private issue on the GitHub repository or contact <m0ogly@proton.me>.
