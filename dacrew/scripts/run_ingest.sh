#!/bin/bash

# Script to run Jira webhook ingestion server
# Usage: ./scripts/run_ingest.sh [options]

set -e

# Configuration
HOST=${JIRA_INGEST_HOST:-"0.0.0.0"}
PORT=${JIRA_INGEST_PORT:-"8080"}
RELOAD=${JIRA_INGEST_RELOAD:-"false"}

echo "🚀 Starting Jira webhook ingestion server..."
echo "📡 Host: $HOST"
echo "🔌 Port: $PORT"
echo "🔄 Reload: $RELOAD"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Make sure environment variables are set."
fi

# Run the ingestion server
python -m dacrew.jira_ingest.cli serve \
    --host "$HOST" \
    --port "$PORT" \
    ${RELOAD:+--reload}
