# dacrew

A server application that evaluates Jira issues for their content quality using
[CrewAI](https://github.com/joaomdmoura/crewAI) agents.

## Features

- Configurable mapping from Jira issue type and status to specialised agents.
- Agents analyse issues and optionally transition their status and post
  comments.
- Uses an in-memory queue so expensive LLM evaluations are processed one at a
  time.
- FastAPI server exposing an endpoint to enqueue evaluations.

## Getting started

1. Create a configuration file:

   ```bash
   cp config.example.json config.json
   ```

   Edit `config.json` with your Jira credentials and project mappings.

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
