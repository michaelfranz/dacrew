#!/bin/bash

# Script to run webhook consumers
# Usage: ./scripts/run_consumer.sh [num_consumers]

set -e

# Default number of consumers
NUM_CONSUMERS=${1:-1}

# Configuration
CONFIG_FILE=${DACREW_CONFIG:-"config.yml"}
REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}
BATCH_SIZE=${ISSUE_BATCH_SIZE:-10}
POLL_INTERVAL=${ISSUE_POLL_INTERVAL_MS:-5000}

echo "🚀 Starting $NUM_CONSUMERS Jira issue consumer(s)..."
echo "📋 Config: $CONFIG_FILE"
echo "🔗 Redis: $REDIS_URL"
echo "📦 Batch size: $BATCH_SIZE"
echo "⏱️  Poll interval: ${POLL_INTERVAL}ms"

# Function to run a single consumer
run_consumer() {
    local consumer_id=$1
    echo "Starting consumer $consumer_id..."
    
    # Set environment variables for this consumer
    export CONSUMER_ID=$consumer_id
    
               # Run the consumer
           python -m dacrew.cli run-issue-consumer \
        --config "$CONFIG_FILE" \
        --redis-url "$REDIS_URL" \
        --batch-size "$BATCH_SIZE" \
        --poll-interval "$POLL_INTERVAL"
}

# Function to cleanup background processes
cleanup() {
    echo "🛑 Stopping all consumers..."
    kill $(jobs -p) 2>/dev/null || true
    wait
    echo "✅ All consumers stopped"
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start consumers
if [ "$NUM_CONSUMERS" -eq 1 ]; then
    # Single consumer - run in foreground
    run_consumer 1
else
    # Multiple consumers - run in background
    for i in $(seq 1 $NUM_CONSUMERS); do
        run_consumer $i &
    done
    
    # Wait for all background processes
    wait
fi
