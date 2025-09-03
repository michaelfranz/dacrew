#!/bin/bash

# Script to run worker processes
# Usage: ./scripts/run_worker.sh [num_workers]

set -e

# Default number of workers
NUM_WORKERS=${1:-1}

# Configuration
REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}
BATCH_SIZE=${WORKER_BATCH_SIZE:-10}
POLL_INTERVAL=${WORKER_POLL_INTERVAL_MS:-5000}
MOCK_PROCESSING=${WORKER_MOCK_PROCESSING:-"true"}

echo "🚀 Starting $NUM_WORKERS worker(s)..."
echo "🔗 Redis: $REDIS_URL"
echo "📦 Batch size: $BATCH_SIZE"
echo "⏱️  Poll interval: ${POLL_INTERVAL}ms"
echo "🎭 Mock processing: $MOCK_PROCESSING"

# Function to run a single worker
run_worker() {
    local worker_id=$1
    echo "Starting worker $worker_id..."

    # Set environment variables for this worker
    export WORKER_ID=$worker_id

    # Run the worker
    python -m dacrew.worker.cli run \
        --redis-url "$REDIS_URL" \
        --batch-size "$BATCH_SIZE" \
        --poll-interval "$POLL_INTERVAL" \
        ${MOCK_PROCESSING:+--mock-processing}
}

# Function to cleanup background processes
cleanup() {
    echo "🛑 Stopping all workers..."
    kill $(jobs -p) 2>/dev/null || true
    wait
    echo "✅ All workers stopped"
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start workers
if [ "$NUM_WORKERS" -eq 1 ]; then
    # Single worker - run in foreground
    run_worker 1
else
    # Multiple workers - run in background
    for i in $(seq 1 $NUM_WORKERS); do
        run_worker $i &
    done

    # Wait for all background processes
    wait
fi
