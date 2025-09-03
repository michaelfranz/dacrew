"""Dacrew - Issue processing with agentic capabilities.

This package provides a modular architecture for processing issues:

- dacrew.jira_ingest: Webhook reception and queue publishing
- dacrew.worker: Message consumption and agentic processing
- dacrew.models: Shared data models and queue infrastructure
- dacrew.common: Shared utilities and common functionality
"""

__version__ = "1.0.0"

# Import main modules for easy access
from . import jira_ingest
from . import worker
from . import models
from . import common

__all__ = [
    "jira_ingest",
    "worker", 
    "models",
    "common",
]
