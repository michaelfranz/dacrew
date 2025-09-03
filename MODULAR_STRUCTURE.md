# Dacrew Modular Structure

## Overview

The Dacrew project has been reorganized into a modular architecture with clear separation of concerns:

- **`dacrew.jira_ingest`**: Webhook reception and queue publishing
- **`dacrew.worker`**: Message consumption and agentic processing  
- **`dacrew.models`**: Shared data models and queue infrastructure
- **`dacrew.common`**: Shared utilities and common functionality

## Module Structure

```
dacrew/
├── common/                    # Shared utilities
│   ├── __init__.py
│   ├── hmac_utils.py         # HMAC signature validation
│   └── logging_utils.py      # Logging configuration
├── models/                    # Shared data models
│   ├── __init__.py
│   ├── jira_models.py        # Jira API models
│   ├── queue_models.py       # Queue message models
│   └── queue.py              # Redis queue infrastructure
├── jira_ingest/              # Webhook ingestion
│   ├── __init__.py
│   ├── config.py             # Module-specific configuration
│   ├── server.py             # FastAPI webhook server
│   └── cli.py                # CLI for ingestion service
├── worker/                   # Agent processing
│   ├── __init__.py
│   ├── config.py             # Module-specific configuration
│   ├── consumer.py           # Message consumer
│   └── cli.py                # CLI for worker service
└── scripts/                  # Deployment scripts
    ├── run_ingest.sh         # Start ingestion service
    └── run_worker.sh         # Start worker service
```

## Key Features

### 1. Modular Configuration
- Each module has its own configuration class
- Environment variables with module-specific prefixes
- Automatic .env file loading
- Command-line argument overrides

### 2. Competing Consumers Architecture
- Redis Streams-based message queue
- Multiple independent consumer processes
- Reliable message delivery and acknowledgment
- Orphaned message recovery

### 3. Shared Infrastructure
- Common utilities for HMAC validation and logging
- Shared Pydantic models for data validation
- Centralized queue management

### 4. Docker Deployment
- Separate containers for each module
- Environment variable configuration
- Health checks and monitoring
- Volume mounts for logs and configuration

## Configuration

### Environment Variables

#### Jira Ingest (`dacrew.jira_ingest`)
- `JIRA_WEBHOOK_SECRET`: Webhook signature secret
- `JIRA_INGEST_HOST`: Server host (default: 0.0.0.0)
- `JIRA_INGEST_PORT`: Server port (default: 8080)
- `JIRA_INGEST_WEBHOOK_ENDPOINT`: Webhook endpoint (default: /webhook/jira)

#### Worker (`dacrew.worker`)
- `WORKER_BATCH_SIZE`: Messages per batch (default: 10)
- `WORKER_POLL_INTERVAL_MS`: Poll interval (default: 5000)
- `WORKER_MOCK_PROCESSING`: Enable mock processing (default: true)
- `WORKER_TIMEOUT`: Agent timeout (default: 300)
- `WORKER_MAX_RETRIES`: Max retries (default: 3)

#### Shared
- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379)
- `DACREW_LOG_DIR`: Log directory (default: logs)

## Usage

### Docker Compose

Start all services:
```bash
docker compose up -d
```

Check status:
```bash
docker compose ps
```

View logs:
```bash
docker compose logs jira_ingest
docker compose logs worker
```

### CLI Commands

#### Jira Ingest
```bash
# Start webhook server
python -m dacrew.jira_ingest.cli serve

# Show configuration
python -m dacrew.jira_ingest.cli config
```

#### Worker
```bash
# Start worker
python -m dacrew.worker.cli run

# Start multiple workers
python -m dacrew.worker.cli run-multiple --num-workers 3

# Show configuration
python -m dacrew.worker.cli config
```

### Deployment Scripts

```bash
# Start ingestion service
./dacrew/scripts/run_ingest.sh

# Start worker service (with multiple workers)
./dacrew/scripts/run_worker.sh 3
```

## Data Flow

1. **Webhook Reception**: Jira sends webhook to `jira_ingest` service
2. **Validation**: HMAC signature validation and payload parsing
3. **Queue Publishing**: Validated webhook is enqueued to Redis Streams
4. **Message Consumption**: `worker` consumers read from queue
5. **Processing**: Agentic tasks (quality evaluation, feedback, etc.)
6. **Acknowledgment**: Processed messages are acknowledged

## Testing

Test the complete flow:
```bash
# Create a test script with webhook payload and HMAC signature
python test_worker.py
```

This script:
- Generates a test webhook payload
- Computes HMAC signature
- Sends request to ingestion service
- Verifies processing by worker

## Benefits

1. **Scalability**: Independent scaling of ingestion and processing
2. **Reliability**: Redis Streams provide reliable message delivery
3. **Modularity**: Clear separation of concerns
4. **Maintainability**: Each module can be developed independently
5. **Deployment**: Separate containers for different concerns
6. **Configuration**: Module-specific configuration management

## Migration Notes

- No backward compatibility maintained
- All imports updated to use new module structure
- Environment variables reorganized with prefixes
- Docker services renamed to reflect modules
- `dacrew.jira_agent` renamed to `dacrew.worker` for generic naming
