from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from dacrew.service import EvaluationService
from .config import AppConfig
from .model import JiraWebhook

# from .service import EvaluationService  # Commented out for mock testing

app = FastAPI(title="Dacrew", description="Jira issue evaluation service")

# Global service instance
service: EvaluationService | None = None

# Logging configuration
def setup_logging() -> None:
    """Setup logging configuration with configurable log directory."""
    # Get log directory from environment variable, default to ./logs
    log_dir = os.getenv("DACREW_LOG_DIR", "./logs")
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path / "dacrew.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def log_server_message(message: str) -> None:
    """Log server messages."""
    logging.info(f"[SERVER] {message}")

def log_webhook_request(webhook_data: Dict[str, Any], query_params: Dict[str, str] = None) -> None:
    """Log webhook request details."""
    try:
        # Get log directory
        log_dir = os.getenv("DACREW_LOG_DIR", "./logs")
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Create timestamped webhook log file
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        webhook_file = log_path / f"webhook-{timestamp}.log"

        with open(webhook_file, "w", encoding="utf-8") as f:
            f.write(f"Webhook received at: {datetime.now().isoformat()}\n")
            if query_params:
                f.write(f"Query parameters: {json.dumps(query_params, indent=2)}\n")
            f.write(f"Webhook payload:\n{json.dumps(webhook_data, indent=2)}\n")

        logging.info(f"Webhook logged to: {webhook_file}")
    except Exception as e:
        logging.error(f"Failed to log webhook request: {e}")

def log_error(error_message: str, request_data: str = "") -> None:
    """Log errors to timestamped error log files."""
    try:
        # Get log directory
        log_dir = os.getenv("DACREW_LOG_DIR", "./logs")
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        error_file = log_path / f"error-{timestamp}.log"

        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"Error: {error_message}\n")
            if request_data:
                f.write(f"Request Data: {request_data}\n")

        logging.error(f"Error logged to: {error_file}")
    except Exception as e:
        logging.error(f"Failed to write error log: {e}")


async def mock_process_webhook_payload(webhook: JiraWebhook, project_key: str, issue_key: str) -> None:
    """Mock processing function for testing webhook handling."""
    log_server_message(f"[MOCK] Starting mock processing for {project_key}/{issue_key}")

    # Extract issue details from the validated Pydantic model
    if webhook.issue and webhook.issue.fields:
        fields = webhook.issue.fields

        # Extract basic issue information using the model
        issue_type = fields.issuetype.name
        status = fields.status.name
        summary = fields.summary
        description = fields.description or "no description"
        priority = fields.priority.name
        assignee = fields.assignee.displayName if fields.assignee else "unassigned"

        log_server_message(f"[MOCK] Issue Type: {issue_type}")
        log_server_message(f"[MOCK] Status: {status}")
        log_server_message(f"[MOCK] Priority: {priority}")
        log_server_message(f"[MOCK] Assignee: {assignee}")
        log_server_message(f"[MOCK] Summary: {summary}")
        log_server_message(f"[MOCK] Description length: {len(description)} characters")

        # Log webhook event type
        log_server_message(f"[MOCK] Webhook Event: {webhook.webhookEvent}")

        # Log changelog information if available
        if webhook.changelog and webhook.changelog.items:
            log_server_message(f"[MOCK] Changelog items: {len(webhook.changelog.items)}")
            for item in webhook.changelog.items:
                log_server_message(f"[MOCK] Changed field: {item.field} from '{item.fromString}' to '{item.toString}'")
    else:
        log_server_message(f"[MOCK] No issue data available in webhook")

    # Simulate processing time (realistic for LLM operations)
    import asyncio
    await asyncio.sleep(2.5)  # Simulate 2.5 seconds processing time (realistic for LLM)

    # Log what would happen in real processing
    log_server_message(f"[MOCK] Would find agent for {issue_type}/{status}")
    log_server_message(f"[MOCK] Would evaluate issue with context")
    log_server_message(f"[MOCK] Would add comment to Jira")
    log_server_message(f"[MOCK] Would transition status if needed")

    log_server_message(f"[MOCK] Mock processing completed for {project_key}/{issue_key}")


def compute_hmac_sha256(data: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for the given data and secret."""
    return hmac.new(
        secret.encode('utf-8'),
        data,
        hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(data: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC signature from X-Hub-Signature header."""
    if not signature_header or not secret:
        return False

    # Extract the signature value (remove 'sha256=' prefix)
    if signature_header.startswith('sha256='):
        expected_signature = signature_header[7:]  # Remove 'sha256=' prefix
    else:
        expected_signature = signature_header

    # Compute the actual signature
    actual_signature = compute_hmac_sha256(data, secret)

    # Compare signatures (use hmac.compare_digest for timing attack protection)
    return hmac.compare_digest(expected_signature, actual_signature)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the service on startup."""
    global service

    # Setup logging first
    setup_logging()
    log_server_message("Server starting up")

    try:
        config = AppConfig.load("config.yml")
        # service = EvaluationService(config)  # Commented out for mock testing
        # service.start()  # Commented out for mock testing
        log_server_message("Mock mode - service initialization skipped")
        log_server_message(f"Server ready on port 8080")
        log_server_message(f"Webhook endpoint: /webhook/jira")
        log_server_message(f"Health check: /health")
    except Exception as e:
        log_server_message(f"Failed to initialize service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up the service on shutdown."""
    global service
    log_server_message("Server shutting down")
    if service:
        await service.stop()
        log_server_message("Service stopped")


@app.post("/embeddings/update/{project_id}")
async def update_embeddings(project_id: str) -> dict:
    """Update embeddings for a project."""
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")

    await service.update_embeddings(project_id)
    return {"message": f"Embeddings updated for project {project_id}"}


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhook/jira")
async def jira_webhook(request: Request) -> dict:
    """Handle Jira webhook requests with HMAC signature validation."""
    # Mock mode - no service dependency
    # if not service:
    #     log_server_message("Webhook request received but service not initialized")
    #     raise HTTPException(status_code=500, detail="Service not initialized")

    # Get request body
    body = await request.body()

    # Log query parameters if present
    query_params = dict(request.query_params)
    if query_params:
        log_server_message(f"Query parameters received: {query_params}")

    # Get webhook secret from config (mock mode)
    try:
        config = AppConfig.load("config.yml")
        webhook_secret = config.jira.webhook_secret
    except Exception as e:
        log_server_message(f"Failed to load config: {e}")
        webhook_secret = ""

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
        webhook = JiraWebhook.model_validate(payload)
        log_server_message(f"Webhook validated successfully: {webhook.webhookEvent}")

    except json.JSONDecodeError as e:
        log_server_message(f"JSON parsing error: {e}")
        log_error(f"Invalid JSON in request body: {e}", body.decode('utf-8', errors='ignore'))
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        log_server_message(f"Failed to validate webhook payload: {e}")
        log_error(f"Validation error: {e}", json.dumps(payload))
        # Continue with partial data as requested
        log_server_message("Continuing with partial data due to validation error")
        webhook = None

    # Extract information for processing using the model
    try:
        if webhook and webhook.issue:
            issue_key = webhook.issue.key
            project_key = webhook.issue.fields.project.key
            webhook_event = webhook.webhookEvent
            issue_event_type = webhook.issue_event_type_name or "unknown"

            log_server_message(f"Processing webhook: {webhook_event} - {issue_event_type} for {project_key}/{issue_key}")

            # Call mock processing function with the validated model
            await mock_process_webhook_payload(webhook, project_key, issue_key)

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

    # Run the server on localhost:8080 for local testing
    uvicorn.run(
        "dacrew.server:app",
        host="localhost",
        port=8080,
        reload=False,
        log_level="info"
    )
