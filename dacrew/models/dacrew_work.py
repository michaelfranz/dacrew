"""Dacrew work models for generic work processing."""

from datetime import datetime
from typing import Union, Literal
from pydantic import BaseModel, Field

from .jira_models import JiraIssueModel


class GithubModel(BaseModel):
    """Stub model for GitHub webhook payloads (for future extensibility)."""
    repository: str
    action: str
    sender: str
    # Add more fields as needed when GitHub support is implemented


class DacrewWork(BaseModel):
    """Generic work representation for Dacrew processing."""
    id: str = Field(..., description="Unique identifier for this work item")
    source: Literal["Jira", "Github"] = Field(..., description="Source system for this work")
    payload: Union[JiraIssueModel, GithubModel] = Field(..., description="Source-specific payload")
    created_at: datetime = Field(default_factory=datetime.now, description="When this work was created")
