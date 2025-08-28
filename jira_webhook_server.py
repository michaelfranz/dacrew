#!/usr/bin/env python3
"""
Jira Webhook Server
A simple server to capture Jira webhook requests and log them to files.
"""

import json
import os
import sys
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JIRA_WEBHOOK_SECRET")
if not SECRET_KEY:
    raise ValueError("JIRA_WEBHOOK_SECRET not found in environment variables")
LOG_DIR = Path("temp/jira")
SERVER_LOG_FILE = LOG_DIR / "server.log"

# Create FastAPI app
app = FastAPI(title="Jira Webhook Server", version="1.0.0")


def compute_hmac_sha256(data: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for the given data and secret."""
    return hmac.new(
        secret.encode('utf-8'),
        data,
        hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(data: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC signature from X-Hub-Signature header."""
    if not signature_header:
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


def log_server_message(message: str) -> None:
    """Log server messages to the server log file."""
    try:
        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(SERVER_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write to server log: {e}", file=sys.stderr)


def log_error(error_message: str, request_data: str = "") -> None:
    """Log errors to timestamped error log files."""
    try:
        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        error_file = LOG_DIR / f"error-{timestamp}.log"
        
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"Error: {error_message}\n")
            if request_data:
                f.write(f"Request Data: {request_data}\n")
    except Exception as e:
        print(f"Failed to write error log: {e}", file=sys.stderr)


def log_webhook_request(data: Dict[str, Any]) -> str:
    """Log webhook request to timestamped file and return filename."""
    try:
        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"jira-{timestamp}.log"
        filepath = LOG_DIR / filename
        
        # Format JSON with 2-space indentation
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(formatted_json)
            f.write("\n")  # Add newline at end
        
        return filename
    except Exception as e:
        error_msg = f"Failed to write webhook log: {e}"
        log_error(error_msg, str(data))
        raise HTTPException(status_code=500, detail=error_msg)


@app.on_event("startup")
async def startup_event():
    """Log server startup."""
    log_server_message("Server starting up")
    print(f"Jira Webhook Server starting on http://localhost:8080")
    print(f"Webhook endpoint: http://localhost:8080/jira")
    print(f"Health check: http://localhost:8080/health")
    print(f"Log directory: {LOG_DIR.absolute()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Log server shutdown."""
    log_server_message("Server shutting down")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/jira")
async def jira_webhook(request: Request):
    """Handle Jira webhook requests."""
    try:
        # Get request body
        body = await request.body()
        
        # Log query parameters if present
        query_params = dict(request.query_params)
        if query_params:
            log_server_message(f"Query parameters received: {query_params}")
        
        # Check for HMAC signature in headers
        signature_header = request.headers.get("X-Hub-Signature")
        if not signature_header:
            error_msg = "Missing X-Hub-Signature header"
            log_server_message(f"Authentication failed: {error_msg}")
            log_error(error_msg, body.decode('utf-8', errors='ignore'))
            raise HTTPException(status_code=401, detail="Missing signature header")
        
        if not verify_hmac_signature(body, signature_header, SECRET_KEY):
            error_msg = "Invalid HMAC signature"
            log_server_message(f"Authentication failed: {error_msg}")
            log_server_message(f"Received signature: {signature_header}")
            log_error(error_msg, body.decode('utf-8', errors='ignore'))
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in request body: {e}"
            log_server_message(f"JSON parsing error: {error_msg}")
            log_error(error_msg, body.decode('utf-8', errors='ignore'))
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Log the webhook request
        filename = log_webhook_request(data)
        
        # Log successful request with query params info
        query_info = f" (query: {query_params})" if query_params else ""
        log_server_message(f"Webhook request processed successfully: {filename}{query_info}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Webhook received and logged",
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "query_params": query_params
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error processing webhook: {e}"
        log_server_message(f"Unexpected error: {error_msg}")
        log_error(error_msg, body.decode('utf-8', errors='ignore') if 'body' in locals() else "")
        raise HTTPException(status_code=500, detail="Internal server error")


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
    # Start the server
    uvicorn.run(
        "jira_webhook_server:app",
        host="localhost",
        port=8080,
        reload=False,
        log_level="info"
    )

