"""FastAPI server for Jira webhook ingestion."""

import json
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from ..common import (
    setup_logging,
    log_server_message,
    log_webhook_request,
    log_error,
    verify_hmac_signature,
)
from ..models import JiraIssueModel, DacrewWork
from ..models.queue import enqueue_dacrew_work
from .config import JiraIngestConfig

# Initialize FastAPI app
app = FastAPI(title="Dacrew Jira Ingest", version="1.0.0")

# Load configuration
config = JiraIngestConfig.from_env()

# Setup logging
setup_logging(config.log_dir)

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """Handle application startup."""
    log_server_message("Server starting up")
    log_server_message(f"Webhook endpoint: {config.webhook_endpoint}")
    log_server_message(f"Health check: /health")
    log_server_message("Server ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    log_server_message("Server shutting down")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "jira_ingest"}


@app.post(config.webhook_endpoint)
async def jira_webhook(request: Request) -> dict:
    """Handle Jira webhook requests with HMAC signature validation."""
    # Get request body
    body = await request.body()
    
    # Get query parameters
    query_params = dict(request.query_params)
    if query_params:
        log_server_message(f"Query parameters received: {query_params}")
    
    # Get webhook secret from config
    webhook_secret = config.webhook_secret
    
    if not webhook_secret:
        log_server_message("Webhook secret not configured")
        log_error("Webhook secret not configured", body.decode('utf-8', errors='ignore'))
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Check for HMAC signature in headers
    signature_header = request.headers.get("X-Hub-Signature")
    if not signature_header:
        log_server_message("Missing X-Hub-Signature header")
        log_error("Missing X-Hub-Signature header", body.decode('utf-8', errors='ignore'))
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature header")

    if not verify_hmac_signature(body, signature_header, webhook_secret):
        log_server_message("Invalid HMAC signature")
        log_server_message(f"Received signature: {signature_header}")
        log_error("Invalid HMAC signature", body.decode('utf-8', errors='ignore'))
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    # Parse and validate webhook payload using Pydantic model
    try:
        payload = json.loads(body)
        log_webhook_request(payload, query_params)

        # Convert to Pydantic model for validation and structured access
        jira_issue_model = JiraIssueModel.model_validate(payload)
        log_server_message(f"Webhook validated successfully: {jira_issue_model.webhookEvent}")

    except json.JSONDecodeError as e:
        log_server_message(f"JSON parsing error: {e}")
        log_error(f"Invalid JSON in request body: {e}", body.decode('utf-8', errors='ignore'))
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        log_server_message(f"Failed to validate webhook payload: {e}")
        log_error(f"Validation error: {e}", json.dumps(payload))
        # Continue with partial data as requested
        log_server_message("Continuing with partial data due to validation error")
        jira_issue_model = None

    # Transform to DacrewWork and enqueue for processing
    try:
        if jira_issue_model and jira_issue_model.issue:
            issue_key = jira_issue_model.issue.key
            project_key = jira_issue_model.issue.fields.project.key
            webhook_event = jira_issue_model.webhookEvent
            issue_event_type = jira_issue_model.issue_event_type_name or "unknown"

            log_server_message(f"Processing webhook: {webhook_event} - {issue_event_type} for {project_key}/{issue_key}")

            # Create DacrewWork object
            work_id = f"{project_key}-{issue_key}-{jira_issue_model.timestamp}"
            dacrew_work = DacrewWork(
                id=work_id,
                source="Jira",
                payload=jira_issue_model
            )

            # Enqueue DacrewWork for processing
            message_id = enqueue_dacrew_work(dacrew_work)
            log_server_message(f"DacrewWork enqueued for processing: {message_id}")

            log_server_message(f"Webhook processed successfully for {project_key}/{issue_key}")
        else:
            log_server_message("Webhook processed but no issue data available")

    except Exception as e:
        log_server_message(f"Error processing webhook: {e}")
        log_error(f"Error processing webhook: {e}", json.dumps(payload))
        raise HTTPException(status_code=500, detail="Error processing webhook")

    # For production, return a simple acknowledgment
    return {
        "status": "success",
        "message": "Webhook processed successfully"
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors."""
    log_server_message(f"404 Not Found: {request.url}")
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "path": str(request.url)}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors."""
    log_server_message(f"500 Internal Server Error: {exc.detail}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        "dacrew.jira_ingest.server:app",
        host=config.host,
        port=config.port,
        reload=False,
        log_level="info"
    )
