"""Shared models for issue processing."""

from .jira_models import (
    JiraIssueModel,
    JiraIssue,
    JiraIssueFields,
    JiraUser,
    JiraProject,
    JiraIssueType,
    JiraStatus,
    JiraPriority,
    JiraComment,
    JiraTransition,
    JiraFieldUpdate,
    create_comment_body,
    create_simple_comment,
    create_transition,
)

from .dacrew_work import (
    DacrewWork,
    GithubModel,
)

from .queue_models import (
    JiraIssueMessage,
    WebhookMessage,
)

__all__ = [
    # Core Jira models
    "JiraIssueModel",
    "JiraIssue",
    "JiraIssueFields",
    "JiraUser",
    "JiraProject",
    "JiraIssueType",
    "JiraStatus",
    "JiraPriority",
    "JiraComment",
    "JiraTransition",
    "JiraFieldUpdate",
    "create_comment_body",
    "create_simple_comment",
    "create_transition",
    # Dacrew work models
    "DacrewWork",
    "GithubModel",
    # Queue models (legacy)
    "JiraIssueMessage",
    "WebhookMessage",
]
