from __future__ import annotations

from typing import Any

from jira import JIRA

from .config import JiraConfig


class JiraClient:
    """Thin wrapper around the Jira API."""

    def __init__(self, cfg: JiraConfig) -> None:
        self._jira = JIRA(server=cfg.url, basic_auth=(cfg.user_id, cfg.token))

    def fetch_issue(self, issue_id: str) -> Any:
        return self._jira.issue(issue_id)

    def add_comment(self, issue_id: str, comment: str) -> None:
        self._jira.add_comment(issue_id, comment)

    def transition(self, issue_id: str, status_name: str) -> None:
        transitions = self._jira.transitions(issue_id)
        transition_id = next((t["id"] for t in transitions if t["name"] == status_name), None)
        if transition_id:
            self._jira.transition_issue(issue_id, transition_id)
