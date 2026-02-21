# ───────────── Stage 1: Build frontend ─────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ───────────── Stage 2: Python runtime ─────────────
FROM python:3.11-slim

# FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ ./backend/

# Frontend build from stage 1
COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV OLLAMA_URL=http://host.docker.internal:11434/api/generate
ENV OLLAMA_MODEL=mistral

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
