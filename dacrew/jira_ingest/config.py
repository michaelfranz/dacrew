"""Configuration for Jira webhook ingestion."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class JiraIngestConfig:
    """Configuration for Jira webhook ingestion."""
    
    # Webhook settings
    webhook_secret: str
    webhook_endpoint: str = "/webhook/jira"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Logging
    log_dir: Optional[str] = None
    
    # Queue settings
    redis_url: str = "redis://localhost:6379"
    
    @classmethod
    def from_env(cls) -> "JiraIngestConfig":
        """Create configuration from environment variables."""
        return cls(
            webhook_secret=os.getenv("JIRA_WEBHOOK_SECRET", ""),
            webhook_endpoint=os.getenv("JIRA_INGEST_WEBHOOK_ENDPOINT", "/webhook/jira"),
            host=os.getenv("JIRA_INGEST_HOST", "0.0.0.0"),
            port=int(os.getenv("JIRA_INGEST_PORT", "8080")),
            log_dir=os.getenv("DACREW_LOG_DIR", "logs"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        )
