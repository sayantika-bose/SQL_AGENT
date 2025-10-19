#!/bin/bash

# Start all services for the SQL Agent application

echo "Starting SQL Agent services..."

# Get the root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Set Python path
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

# Function to cleanup on exit
cleanup() {
    echo "Stopping all services..."
    pkill -P $$
    redis-cli shutdown || true
    exit
}

trap cleanup SIGINT SIGTERM

# Start Redis in the background
echo "Starting Redis..."
redis-server --daemonize yes --port 6379

# Wait for Redis to be ready
echo "Waiting for Redis to start..."
sleep 2

# Start Data API in the background
echo "Starting Data API on port 8001..."
(cd "$ROOT_DIR/query_expert_app/data_api" && poetry run python -m data_api.main) &
DATA_API_PID=$!

# Wait for Data API to be ready
sleep 3

# Start Worker in the background
echo "Starting Celery Worker..."
(cd "$ROOT_DIR/query_expert_app/worker" && poetry run python -m worker.main) &
WORKER_PID=$!

# Wait for Worker to be ready
sleep 3

# Start API in the background
echo "Starting Main API on port 8000..."
(cd "$ROOT_DIR/query_expert_app/api" && poetry run python -m api.main) &
API_PID=$!

# Wait for API to be ready
sleep 3

# Start Angular frontend
echo "Starting Angular frontend on port 5000..."
cd "$ROOT_DIR/frontend" && npm start

# Wait for all background processes
wait
