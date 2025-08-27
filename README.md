# dacrew

A server application that evaluates Jira issues for their content quality using
[CrewAI](https://github.com/joaomdmoura/crewAI) agents with intelligent context from codebases and documentation.

## Features

- **Multi-Project Support**: Configure any number of Jira projects accessible from a single Atlassian API token
- **Intelligent Context**: Automatically generates embeddings from codebases and documentation to provide relevant context to agents
- **Configurable Agents**: Map Jira issue types and statuses to specialized agents
- **Automated Workflows**: Agents analyze issues and optionally transition their status and post comments
- **Embedding Management**: Incremental updates with configurable frequency to minimize expensive operations
- **Containerized Deployment**: Ready for deployment in any environment with Docker support
- **Queue Processing**: In-memory queue ensures expensive LLM evaluations are processed sequentially
- **FastAPI Server**: RESTful API with health checks and project management endpoints

## Architecture

### Embedding System
- **Codebase Integration**: Clone git repositories and extract relevant code snippets
- **Documentation Processing**: Support for local files and remote URLs
- **Incremental Updates**: Smart caching with configurable update frequencies
- **Context Retrieval**: Semantic search to find relevant code/documentation for issue evaluation

### Deployment Options
- **Local Development**: Docker Compose for easy local testing
- **AWS ECS**: Production-ready deployment with auto-scaling
- **Custom Environments**: Flexible deployment scripts for any hosting provider

## Getting Started

### 1. Configuration

Create a configuration file:

```bash
cp config.example.yml config.yml
```

Edit `config.yml` with your Jira credentials and project mappings:

```yaml
jira:
  url: https://your-domain.atlassian.net
  user_id: your-user@example.com
  token: your-api-token

embedding:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size: 512
  chunk_overlap: 50
  workspace_path: "./embeddings"
  max_workers: 4

projects:
  - project_id: "PROJ"
    type_status_map:
      Bug:
        To Do: todo-evaluator
        Ready for Development: ready-for-development-evaluator
    codebase:
      repo: "https://github.com/your-org/your-repo"
      include_patterns:
        - "src/**/*.java"
        - "src/**/*.py"
      exclude_patterns:
        - "node_modules/**"
        - "build/**"
      update_frequency_hours: 24
    documents:
      paths:
        - "docs/README.md"
        - "docs/API.md"
      urls:
        - "https://your-docs.com/api-reference"
      update_frequency_hours: 168  # 1 week
```

### 2. Local Development

#### Option A: Python Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn dacrew.server:app --reload
```

#### Option B: Docker Compose
```bash
# Build and run with Docker Compose
docker-compose up --build
```

### 3. Update Embeddings

Before evaluating issues, update embeddings for your projects:

```bash
# Update embeddings for a specific project
curl -X POST http://localhost:8000/embeddings/update/PROJ

# Or trigger via the API
curl -X POST http://localhost:8000/evaluate/PROJ/ISSUE-1
```

### 4. Evaluate Issues

Trigger an evaluation via HTTP:

```bash
curl -X POST http://localhost:8000/evaluate/PROJ/ISSUE-1
```

## API Endpoints

- `POST /evaluate/{project_id}/{issue_id}` - Evaluate a Jira issue
- `POST /embeddings/update/{project_id}` - Update embeddings for a project
- `GET /health` - Health check
- `GET /projects` - List configured projects

## Deployment

### Local Development
```bash
# Run build script
chmod +x scripts/build.sh
./scripts/build.sh

# Start with Docker Compose
docker-compose up
```

### AWS Deployment
```bash
# Configure AWS credentials
aws configure

# Deploy to AWS ECS
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Custom Environment
The deployment script can be customized for any hosting provider by modifying `scripts/deploy.sh`.

## Configuration Reference

### Project Configuration
- `project_id`: Jira project key
- `type_status_map`: Mapping of issue types and statuses to agent types
- `codebase`: Git repository configuration for code embeddings
- `documents`: Local files and URLs for documentation embeddings
- `embedding`: Project-specific embedding settings (optional)

### Embedding Configuration
- `model`: Sentence transformer model for embeddings
- `chunk_size`: Size of text chunks for processing
- `chunk_overlap`: Overlap between chunks
- `workspace_path`: Directory for storing embeddings
- `max_workers`: Number of parallel workers for processing

## Development

### Running Tests
```bash
python -m pytest tests/ -v
```

### Code Quality
```bash
# Format code
black dacrew/ tests/

# Sort imports
isort dacrew/ tests/

# Type checking
mypy dacrew/
```

### Building Docker Image
```bash
docker build -t dacrew .
```

## Architecture Notes

The agents defined here are placeholders; they demonstrate how CrewAI can be
integrated and can be extended with real LLM prompts and embedding logic.

### Embedding Workflow
1. **Repository Cloning**: Git repositories are cloned/updated based on configuration
2. **File Processing**: Code files are processed according to include/exclude patterns
3. **Text Chunking**: Content is split into overlapping chunks for better context
4. **Embedding Generation**: Chunks are converted to embeddings using sentence transformers
5. **Storage**: Embeddings and metadata are stored in project-specific workspaces
6. **Retrieval**: During evaluation, relevant context is retrieved using semantic search

### Deployment Architecture
- **Container**: Lightweight Python 3.11 container with all dependencies
- **Health Checks**: Built-in health monitoring for container orchestration
- **Logging**: Structured logging to CloudWatch (AWS) or stdout
- **Scaling**: Horizontal scaling support through ECS or Kubernetes
