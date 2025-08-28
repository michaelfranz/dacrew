"""Pydantic models for Jira API interactions and webhook handling."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict


class JiraAvatarUrls(BaseModel):
    """Jira avatar URLs for users and projects."""
    model_config = ConfigDict(extra="ignore")
    
    url_48x48: Optional[str] = Field(None, alias="48x48")
    url_24x24: Optional[str] = Field(None, alias="24x24") 
    url_16x16: Optional[str] = Field(None, alias="16x16")
    url_32x32: Optional[str] = Field(None, alias="32x32")


class JiraUser(BaseModel):
    """Jira user information."""
    model_config = ConfigDict(extra="ignore")
    
    self: Optional[str] = None
    accountId: str
    avatarUrls: Optional[JiraAvatarUrls] = None
    displayName: str
    active: Optional[bool] = None
    timeZone: Optional[str] = None
    accountType: Optional[str] = None


class JiraStatusCategory(BaseModel):
    """Jira status category information."""
    model_config = ConfigDict(extra="ignore")
    
    self: Optional[str] = None
    id: Optional[int] = None
    key: Optional[str] = None
    colorName: Optional[str] = None
    name: Optional[str] = None


class JiraStatus(BaseModel):
    """Jira issue status information."""
    model_config = ConfigDict(extra="ignore")
    
    self: Optional[str] = None
    description: Optional[str] = None
    iconUrl: Optional[str] = None
    name: str
    id: str
    statusCategory: Optional[JiraStatusCategory] = None


class JiraPriority(BaseModel):
    """Jira issue priority information."""
    model_config = ConfigDict(extra="ignore")
    
    self: Optional[str] = None
    iconUrl: Optional[str] = None
    name: str
    id: str


class JiraIssueType(BaseModel):
    """Jira issue type information."""
    model_config = ConfigDict(extra="ignore")
    
    self: Optional[str] = None
    id: str
    description: Optional[str] = None
    iconUrl: Optional[str] = None
    name: str
    subtask: Optional[bool] = None
    avatarId: Optional[int] = None
    entityId: Optional[str] = None
    hierarchyLevel: Optional[int] = None


class JiraProject(BaseModel):
    """Jira project information."""
    model_config = ConfigDict(extra="ignore")
    
    self: Optional[str] = None
    id: str
    key: str
    name: str
    projectTypeKey: Optional[str] = None
    simplified: Optional[bool] = None
    avatarUrls: Optional[JiraAvatarUrls] = None


class JiraProgress(BaseModel):
    """Jira progress information."""
    model_config = ConfigDict(extra="ignore")
    
    progress: int
    total: int


class JiraIssueFields(BaseModel):
    """Jira issue fields - core fields that your application needs."""
    model_config = ConfigDict(extra="ignore")
    
    # Required fields for your application
    summary: str
    description: Optional[str] = None
    status: JiraStatus
    priority: JiraPriority
    project: JiraProject
    issuetype: JiraIssueType
    
    # Optional but commonly used fields
    assignee: Optional[JiraUser] = None
    reporter: Optional[JiraUser] = None
    creator: Optional[JiraUser] = None
    
    # Additional fields that might be useful
    created: Optional[str] = None
    updated: Optional[str] = None
    resolution: Optional[Dict[str, Any]] = None
    labels: Optional[List[str]] = None
    components: Optional[List[Dict[str, Any]]] = None
    fixVersions: Optional[List[Dict[str, Any]]] = None
    versions: Optional[List[Dict[str, Any]]] = None
    duedate: Optional[str] = None
    progress: Optional[JiraProgress] = None
    aggregateprogress: Optional[JiraProgress] = None
    
    # Allow any additional fields that Jira might send
    # This ensures we don't break if Jira adds new fields


class JiraIssue(BaseModel):
    """Jira issue information."""
    model_config = ConfigDict(extra="ignore")
    
    id: str
    self: Optional[str] = None
    key: str
    fields: JiraIssueFields


class JiraChangelogItem(BaseModel):
    """Individual changelog item."""
    model_config = ConfigDict(extra="ignore")
    
    field: str
    fieldtype: Optional[str] = None
    fieldId: Optional[str] = None
    from_: Optional[Any] = Field(None, alias="from")
    fromString: Optional[str] = None
    to: Optional[Any] = None
    toString: Optional[str] = None


class JiraChangelog(BaseModel):
    """Jira changelog information."""
    model_config = ConfigDict(extra="ignore")
    
    id: str
    items: List[JiraChangelogItem]


class JiraWebhook(BaseModel):
    """Comprehensive Jira webhook model that handles all webhook types."""
    model_config = ConfigDict(extra="ignore")
    
    # Core webhook fields
    timestamp: int
    webhookEvent: str
    issue_event_type_name: Optional[str] = None
    
    # Issue information (for issue-related webhooks)
    issue: Optional[JiraIssue] = None
    
    # User information
    user: Optional[JiraUser] = None
    
    # Changelog (for issue updates)
    changelog: Optional[JiraChangelog] = None
    
    # Comment information (for comment-related webhooks)
    comment: Optional[Dict[str, Any]] = None
    
    # Allow any additional fields that Jira might send


# Models for outgoing Jira API calls

class JiraCommentBody(BaseModel):
    """Jira comment body structure."""
    type: str = "doc"
    version: int = 1
    content: List[Dict[str, Any]]


class JiraComment(BaseModel):
    """Model for creating/updating Jira comments."""
    model_config = ConfigDict(extra="ignore")
    
    body: str | JiraCommentBody
    visibility: Optional[Dict[str, str]] = None


class JiraTransition(BaseModel):
    """Model for transitioning Jira issue status."""
    model_config = ConfigDict(extra="ignore")
    
    transition: Dict[str, str]
    fields: Optional[Dict[str, Any]] = None
    update: Optional[Dict[str, Any]] = None


class JiraFieldUpdate(BaseModel):
    """Model for updating Jira issue fields."""
    model_config = ConfigDict(extra="ignore")
    
    fields: Dict[str, Any]
    update: Optional[Dict[str, Any]] = None


# Helper functions for working with the models

def create_comment_body(text: str) -> JiraCommentBody:
    """Create a Jira comment body from plain text."""
    return JiraCommentBody(
        content=[
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]
    )


def create_simple_comment(text: str) -> JiraComment:
    """Create a simple Jira comment from plain text."""
    return JiraComment(body=text)


def create_transition(transition_id: str) -> JiraTransition:
    """Create a Jira transition request."""
    return JiraTransition(transition={"id": transition_id})
