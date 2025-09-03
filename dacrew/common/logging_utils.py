"""Logging utilities for consistent logging across modules."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def setup_logging(log_dir: Optional[str] = None) -> None:
    """Setup logging configuration."""
    log_dir = log_dir or os.getenv("DACREW_LOG_DIR", "logs")
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path / "dacrew.log"),
            logging.StreamHandler()
        ]
    )


def log_server_message(message: str) -> None:
    """Log server-related messages."""
    logging.info(f"[SERVER] {message}")


def log_webhook_request(webhook_data: Dict[str, Any], query_params: Dict[str, str] = None) -> None:
    """Log webhook request details."""
    try:
        # Get log directory
        log_dir = os.getenv("DACREW_LOG_DIR", "logs")
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped webhook log file
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        webhook_file = log_path / f"webhook-{timestamp}.log"
        
        # Write webhook data to file
        with open(webhook_file, "w", encoding="utf-8") as f:
            f.write(f"Webhook received at: {datetime.now().isoformat()}\n")
            if query_params:
                f.write(f"Query parameters: {json.dumps(query_params, indent=2)}\n")
            f.write(f"Webhook payload:\n{json.dumps(webhook_data, indent=2)}\n")
        
        logging.info(f"Webhook logged to: {webhook_file}")
        
    except Exception as e:
        logging.error(f"Failed to log webhook request: {e}")


def log_error(error_message: str, error_data: str = "") -> None:
    """Log error messages with optional error data."""
    try:
        # Get log directory
        log_dir = os.getenv("DACREW_LOG_DIR", "logs")
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped error log file
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        error_file = log_path / f"error-{timestamp}.log"
        
        # Write error data to file
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"Error occurred at: {datetime.now().isoformat()}\n")
            f.write(f"Error message: {error_message}\n")
            if error_data:
                f.write(f"Error data:\n{error_data}\n")
        
        logging.error(f"Error logged to: {error_file}")
        
    except Exception as e:
        logging.error(f"Failed to log error: {e}")
