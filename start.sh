#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Helpers ──────────────────────────────────────────

kill_port() {
    netstat -ano 2>/dev/null | grep ":$1 " | grep LISTENING | awk '{print $5}' | sort -u | while read pid; do
        taskkill //F //PID "$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    done
}

check_prereqs() {
    command -v python >/dev/null 2>&1 || { echo "ERROR: Python required"; return 1; }
    command -v node >/dev/null 2>&1   || { echo "ERROR: Node.js required"; return 1; }
    command -v ffmpeg >/dev/null 2>&1  || echo "WARNING: FFmpeg not found"
    echo "OK: python, node, ffmpeg"
}

install_deps() {
    if [ ! -d "frontend/node_modules" ]; then
        echo ">>> npm install..."
        (cd frontend && npm install)
    else
        echo ">>> node_modules OK"
    fi
    pip install -q -r backend/requirements.txt 2>/dev/null || true
    echo ">>> Dependencies OK"
}

run_build() {
    echo ">>> Building frontend..."
    (cd frontend && npm run build) || { echo "ERROR: Build failed!"; return 1; }
    echo ">>> Build OK"
}

run_tests() {
    echo ">>> Running tests..."
    (cd frontend && npx vitest run) || { echo "ERROR: Tests failed!"; return 1; }
    echo ">>> Tests OK"
}

start_backend() {
    kill_port 8000
    echo ">>> Backend at http://localhost:8000"
    (cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
    BACKEND_PID=$!
}

start_frontend() {
    kill_port 5173
    echo ">>> Frontend at http://localhost:5173"
    (cd frontend && npm run dev) &
    FRONTEND_PID=$!
}

wait_servers() {
    echo ""
    echo "============================================"
    [ -n "$FRONTEND_PID" ] && echo "  Dev:        http://localhost:5173"
    [ -n "$BACKEND_PID" ]  && echo "  Production: http://localhost:8000"
    echo "  Ctrl+C to stop"
    echo "============================================"
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
    wait
}

# ── Menu ─────────────────────────────────────────────

show_menu() {
    echo ""
    echo "=== Whisper Translator ==="
    echo ""
    echo "  1) Start all (build + tests + backend + frontend)"
    echo "  2) Start backend only"
    echo "  3) Start frontend only"
    echo "  4) Build frontend"
    echo "  5) Run tests"
    echo "  6) Build + tests"
    echo "  7) Check prerequisites"
    echo "  8) Install dependencies"
    echo "  0) Quit"
    echo ""
    read -rp "Choose [1-8, 0]: " choice
}

# ── Main ─────────────────────────────────────────────

run_choice() {
    local choice="$1"
    case "$choice" in
        1)
            check_prereqs || continue
            install_deps
            run_build || continue
            run_tests || continue
            start_backend
            start_frontend
            wait_servers
            ;;
        2)
            check_prereqs || continue
            install_deps
            start_backend
            wait_servers
            ;;
        3)
            check_prereqs || continue
            install_deps
            start_frontend
            wait_servers
            ;;
        4)
            run_build
            ;;
        5)
            run_tests
            ;;
        6)
            run_build || continue
            run_tests
            ;;
        7)
            check_prereqs
            ;;
        8)
            install_deps
            ;;
        0)
            echo "Bye!"
            exit 0
            ;;
        *)
            echo "Invalid choice"
            ;;
    esac
}

# If argument passed, run directly: bash start.sh 2
if [ -n "$1" ]; then
    run_choice "$1"
    exit $?
fi

# Interactive menu
while true; do
    show_menu
    run_choice "$choice"
done
