#!/bin/bash
set -euo pipefail
shopt -s extglob

MODE=${1:-deploy}
PROJECT_ROOT=$(pwd)

# Store PIDs for cleanup
PIDS=()

# Cleanup function
cleanup() {
    echo "Shutting down all services..."
    
    # Kill background jobs started by this script first
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Killing PID $pid"
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    
    # Give processes time to shut down gracefully
    sleep 2
    
    # Force kill any remaining background jobs
    jobs -p | xargs -r kill -9 2>/dev/null || true
    
    # Kill processes by port (FastAPI, Frontend, Dashboard)
    echo "Killing processes on ports 8000, 3000, 3001..."
    lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    lsof -ti:3000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    lsof -ti:3001 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    
    # Kill Celery workers (more comprehensive)
    echo "Killing Celery workers..."
    pkill -f "celery.*worker" 2>/dev/null || true
    pkill -f "celery-worker" 2>/dev/null || true
    pkill -f "celery_app" 2>/dev/null || true
    
    # Kill uvicorn processes
    echo "Killing uvicorn processes..."
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    
    # Kill Node.js development servers
    echo "Killing Node.js dev servers..."
    pkill -f "react-scripts start" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    
    # Shutdown Redis
    echo "Shutting down Redis..."
    redis-cli shutdown 2>/dev/null || true
    pkill -f "redis-server" 2>/dev/null || true
    
    # Final cleanup - kill any remaining processes by name patterns
    sleep 1
    pkill -f "backend.*worker" 2>/dev/null || true
    
    echo "Cleanup complete"
    exit 0
}

if [[ $MODE == "dev" || $MODE == "prod" ]]; then
    trap cleanup SIGINT SIGTERM EXIT
fi

# PYTHONPATH setup
export PYTHONPATH="${PYTHONPATH:-}:${PROJECT_ROOT}/replit/backend"

if [ "$MODE" == "dev" ]; then
    echo "Running in development mode"
    if [ -f backend/.venv/bin/activate ]; then
        source backend/.venv/bin/activate
    fi

    echo "Starting Redis..."
    redis-server --daemonize yes --port 6379 --bind 127.0.0.1 &
    PIDS+=($!)
    
    echo "Starting Celery worker..."
    cd backend && celery -A celery_app worker --loglevel=info --concurrency=1 --pool=solo &
    PIDS+=($!)
    cd "$PROJECT_ROOT"
    
    echo "Starting FastAPI server..."
    # Use dynamic port: platform PORT env var, fallback to APP_PORT from .env, default to 8000
    FASTAPI_PORT=${PORT:-$(grep "^APP_PORT=" backend/.env | cut -d'=' -f2 | tr -d '"' || echo "8000")}
    cd backend && uvicorn main:app --reload --port $FASTAPI_PORT --host 0.0.0.0 &
    PIDS+=($!)
    cd "$PROJECT_ROOT"
    
    echo "Starting Dashboard (Next.js)..."
    cd dashboard && npm install && PORT=3001 npm run dev &
    PIDS+=($!)
    cd "$PROJECT_ROOT"
    
    echo "Starting Frontend (React)..."
    cd frontend && npm install && PORT=3000 npm run dev &
    PIDS+=($!)
    cd "$PROJECT_ROOT"

    sleep 2
    echo "All services started with PIDs: ${PIDS[*]}"
    echo "Available URLs:"
    echo "  Dashboard: http://localhost:3001/dashboard"
    echo "  Frontend Demo: http://localhost:3000/chatbot?user_id=001&home_country=Germany&host_country=Canada"
    echo "Press Ctrl+C to stop all services"
    wait

elif [ "$MODE" == "prod" ]; then
    echo "Running in production mode"
    
    echo "Starting Redis..."
    redis-server --save 60 1 --appendonly yes --port 6379 --bind 127.0.0.1 &
    PIDS+=($!)
    
    echo "Starting Celery worker..."
    cd backend && celery -A celery_app worker --loglevel=info --concurrency=4 --pool=solo &
    PIDS+=($!)
    cd "$PROJECT_ROOT"
    
    echo "Starting FastAPI server..."
    cd backend && uvicorn main:app --port 8000 --host 0.0.0.0 --workers 8 &
    PIDS+=($!)
    cd "$PROJECT_ROOT"
    
    # cd replit/dashboard && npx --no-install serve -s out -l 3001 & cd "$PROJECT_ROOT"
    # cd replit/frontend && npx --no-install serve -s build -l 3000 & cd "$PROJECT_ROOT"

    sleep 2
    echo "All services started with PIDs: ${PIDS[*]}"
    echo "Available URLs:"
    echo "  Dashboard: http://127.0.0.1:8000/dashboard"
    echo "  Frontend Demo: http://127.0.0.1:8000/chatbot?user_id=001&home_country=Germany&host_country=Canada"
    echo "Press Ctrl+C to stop all services"
    wait

elif [ "$MODE" == "build" ]; then
    echo "Building production environment"
    
    # Dashboard
    cd dashboard
    npm ci --omit=dev
    npm install serve@14.2.4 --save-dev
    export NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
    npm run build
    cd "$PROJECT_ROOT"

    # Frontend
    cd frontend
    npm ci --omit=dev
    npm install serve@14.2.4 --save-dev
    export REACT_APP_API_BASE_URL=http://127.0.0.1:8000
    npm run build
    cd "$PROJECT_ROOT"

    rm -rf ~/.npm/_npx ~/.npm/_cacache
    
    # strip tests & byte-code from site-packages
    site=$(python -c 'import sysconfig, pathlib, sys; print(pathlib.Path(sysconfig.get_paths()["purelib"]))')
    
    find "$site" -type d -name tests       -prune -exec rm -rf {} +
    find "$site" -type d -name __pycache__ -prune -exec rm -rf {} +
    find "$site" -type f -name '*.py[co]'            -delete
    
    echo "Build complete"
    
    du -h -d1 | sort -h

else
    echo "Usage: $0 [dev|prod|build]"
    exit 1
fi