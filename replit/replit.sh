#!/bin/bash
set -euo pipefail
shopt -s extglob

MODE=${1:-deploy}
PROJECT_ROOT=$(pwd)

# Cleanup function
cleanup() {
    echo "Shutting down all services..."
    
    # Kill background jobs started by this script
    jobs -p | xargs -r kill 2>/dev/null || true
    sleep 1
    
    # Kill processes by port (FastAPI, Frontend, Dashboard)
    lsof -ti:8000 3000 3001 | xargs -r kill -9 2>/dev/null || true
    
    # Kill Celery workers (more comprehensive)
    pkill -f "celery.*worker" 2>/dev/null || true
    pkill -f "celery-worker" 2>/dev/null || true
    
    # Kill any remaining Python processes that might be background workers
    pkill -f "celery_app" 2>/dev/null || true
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    
    # Kill Node.js development servers
    pkill -f "react-scripts start" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    
    # Shutdown Redis
    redis-cli shutdown 2>/dev/null || true
    
    # Final cleanup - kill any remaining processes by name patterns
    sleep 1
    pkill -f "backend.*worker" 2>/dev/null || true
    
    echo "Cleanup complete"
    exit 0
}

if [[ $MODE == dev ]]; then
  trap cleanup SIGINT SIGTERM
fi

# PYTHONPATH setup
export PYTHONPATH="${PYTHONPATH:-}:${PROJECT_ROOT}/replit/backend"

if [ "$MODE" == "dev" ]; then
    echo "Running in development mode"
    if [ -f backend/.venv/bin/activate ]; then
        source backend/.venv/bin/activate
    fi

    redis-server --daemonize yes --port 6379 --bind 127.0.0.1 &
    cd backend && celery -A celery_app worker --loglevel=info --concurrency=1 --pool=solo & cd "$PROJECT_ROOT"
    cd backend && uvicorn main:app --reload --port 8000 & cd "$PROJECT_ROOT"
    cd dashboard && npm install && PORT=3001 npm run dev & cd "$PROJECT_ROOT"
    cd frontend && npm install && PORT=3000 npm run dev & cd "$PROJECT_ROOT"

    sleep 2
    echo "All services started"
    echo "Available URLs:"
    echo "  Dashboard: http://localhost:3001/dashboard"
    echo "  Frontend Demo: http://localhost:3000/chatbot?user_id=001&home_country=Germany&host_country=Canada"
    wait

elif [ "$MODE" == "prod" ]; then
    echo "Running in production mode"
    
    redis-server --save 60 1 --appendonly yes --port 6379 --bind 127.0.0.1 &
    cd replit/backend && celery -A celery_app worker --loglevel=info --concurrency=4 --pool=solo & cd "$PROJECT_ROOT"
    cd replit/backend && uvicorn main:app --port 8000 --host 0.0.0.0 --workers 8 & cd "$PROJECT_ROOT"
    # cd replit/dashboard && npx --no-install serve -s out -l 3001 & cd "$PROJECT_ROOT"
    # cd replit/frontend && npx --no-install serve -s build -l 3000 & cd "$PROJECT_ROOT"

    sleep 2
    echo "All services started"
    echo "Available URLs:"
    echo "  Dashboard: https://ragtest2.replit.app/dashboard"
    echo "  Frontend Demo: https://ragtest2.replit.app/chatbot?user_id=001&home_country=Germany&host_country=Canada"
    wait

elif [ "$MODE" == "build" ]; then
    echo "Building production environment"
    
    # Dashboard
    cd replit/dashboard
    npm ci --omit=dev
    npm install serve@14.2.4 --save-dev
    export NEXT_PUBLIC_API_BASE_URL=https://ragtest2.replit.app
    npm run build
    cd "$PROJECT_ROOT"

    # Frontend
    cd replit/frontend
    npm ci --omit=dev
    npm install serve@14.2.4 --save-dev
    export REACT_APP_API_BASE_URL=https://ragtest2.replit.app
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