"""Queue message models for Jira issue processing."""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class JiraIssueMessage(BaseModel):
    """Message structure for Jira issue processing in the queue."""
    message_id: str  # Unique identifier for this queue message
    timestamp: str  # ISO format timestamp when the message was created
    webhook_event: str  # Type of Jira webhook event (e.g., "jira:issue_updated")
    project_key: str  # Jira project key (e.g., "TEST", "BTS")
    issue_key: str  # Jira issue key (e.g., "TEST-123", "BTS-16")
    jira_issue_model: Dict[str, Any]  # Complete JiraIssueModel data
    query_params: Optional[Dict[str, str]] = None  # URL query parameters from original webhook request


class WebhookMessage(BaseModel):
    """Legacy webhook message structure (for backward compatibility)."""
    webhook_id: str
    timestamp: str
    webhook_event: str
    project_key: str
    issue_key: str
    payload: Dict[str, Any]
    query_params: Optional[Dict[str, str]] = None
