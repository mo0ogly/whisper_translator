.PHONY: dev dev-backend dev-frontend install build docker docker-up docker-down test lint clean

# ──────────── Development ────────────

install:  ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev-backend:  ## Start FastAPI dev server
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:  ## Start Vite dev server
	cd frontend && npm run dev

dev:  ## Start backend + frontend (requires 2 terminals)
	@echo "Run in separate terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

# ──────────── Build ──────────────────

build:  ## Build frontend for production
	cd frontend && npm run build

# ──────────── Docker ─────────────────

docker:  ## Build Docker image
	docker build -t whisper-translator .

docker-up:  ## Start with docker compose
	docker compose up -d

docker-down:  ## Stop docker compose
	docker compose down

# ──────────── Quality ────────────────

test:  ## Run unit tests
	cd backend && python -m pytest tests/ -v

lint:  ## Check Python syntax
	cd backend && python -m py_compile main.py

# ──────────── Cleanup ────────────────

clean:  ## Remove build artifacts
	rm -rf frontend/dist frontend/node_modules backend/__pycache__ backend/tests/__pycache__

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'
