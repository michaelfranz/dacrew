"""Worker processing module.

This module handles:
- Consuming messages from the queue
- Processing issues with agentic tasks
- Quality evaluation, feedback, code generation, etc.
"""

from .consumer import IssueConsumer
from .config import WorkerConfig

__all__ = [
    "IssueConsumer",
    "WorkerConfig",
]
