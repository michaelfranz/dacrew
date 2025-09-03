"""Configuration for worker processing."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class WorkerConfig:
    """Configuration for worker processing."""
    
    # Queue settings
    redis_url: str = "redis://localhost:6379"
    batch_size: int = 10
    poll_interval_ms: int = 5000
    
    # Processing settings
    mock_processing: bool = True  # For testing and development
    
    # Logging
    log_dir: Optional[str] = None
    
    # Agent settings (for future CrewAI integration)
    agent_timeout: int = 300  # seconds
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> "WorkerConfig":
        """Create configuration from environment variables."""
        return cls(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            batch_size=int(os.getenv("WORKER_BATCH_SIZE", "10")),
            poll_interval_ms=int(os.getenv("WORKER_POLL_INTERVAL_MS", "5000")),
            mock_processing=os.getenv("WORKER_MOCK_PROCESSING", "true").lower() == "true",
            log_dir=os.getenv("DACREW_LOG_DIR", "logs"),
            agent_timeout=int(os.getenv("WORKER_TIMEOUT", "300")),
            max_retries=int(os.getenv("WORKER_MAX_RETRIES", "3")),
        )
