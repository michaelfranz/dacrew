"""Jira webhook ingestion module.

This module handles:
- Receiving Jira webhooks
- Validating webhook signatures
- Normalizing webhook data
- Publishing to the message queue
"""

from .server import app
from .config import JiraIngestConfig

__all__ = [
    "app",
    "JiraIngestConfig",
]
