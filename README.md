# dacrew

A server application that evaluates Jira issues for their content quality using
[CrewAI](https://github.com/joaomdmoura/crewAI) agents.

## Features

- Configurable mapping from Jira issue type and status to specialised agents.
- Agents analyse issues and optionally transition their status and post
  comments.
- Uses an in-memory queue so expensive LLM evaluations are processed one at a
  time.
- FastAPI server exposing an endpoint to enqueue evaluations and manages a
  background worker for processing tasks.

## Getting started

1. Create a configuration file:

   ```bash
   cp config.example.yml config.yml
   ```

   Edit `config.yml` with your Jira credentials and project mappings.

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:

   ```bash
   uvicorn dacrew.server:app --reload
   ```

4. Trigger an evaluation via HTTP:

   ```bash
   curl -X POST http://localhost:8000/evaluate/PROJ/ISSUE-1
   ```

The agents defined here are placeholders; they demonstrate how CrewAI can be
integrated and can be extended with real LLM prompts and embedding logic.

## Branching model

Development work should occur on feature branches cut from the `development`
branch. The `main` branch is reserved for stable releases and is updated by
rebasing from `development`. Pushing to `main` triggers the deployment
workflow described below.

## Running with Docker

1. Build the container image:

   ```bash
   docker build -t dacrew .
   ```

2. Provide a configuration file and run the container:

   ```bash
   docker run -p 8000:8000 -v $(pwd)/config.yml:/config/config.yml dacrew
   ```

   The application reads its configuration from the path specified in the
   `DACREW_CONFIG` environment variable, defaulting to `/config/config.yml`.

## Continuous deployment

GitHub Actions builds and pushes a Docker image to Amazon ECR whenever new
commits reach `main`. The workflow then forces a new deployment of the
configured ECS service. To enable this, define the following repository
secrets: `AWS_ROLE_TO_ASSUME`, `AWS_REGION`, `ECR_REPOSITORY`, `ECS_CLUSTER`,
and `ECS_SERVICE`.

