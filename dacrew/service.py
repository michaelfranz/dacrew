from __future__ import annotations

import asyncio
from typing import Dict, Type

from .agents.base import EvaluationResult, BaseAgent
from .agents.ready import ReadyForDevelopmentEvaluator
from .agents.todo import TodoEvaluator
from .config import AppConfig
from .embeddings import EmbeddingManager
from .jira_client import JiraClient

AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "todo-evaluator": TodoEvaluator,
    "ready-for-development-evaluator": ReadyForDevelopmentEvaluator,
}


class EvaluationService:
    """Coordinates the evaluation of Jira issues."""

    def __init__(self, cfg: AppConfig) -> None:
        self.config = cfg
        self.jira = JiraClient(cfg.jira)
        self.embedding_manager = EmbeddingManager(cfg)
        self.queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self.worker_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the background worker task."""

        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        """Stop the background worker task."""

        if self.worker_task is not None:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                pass

    async def _worker(self) -> None:
        while True:
            try:
                project_id, issue_id = await self.queue.get()
            except asyncio.CancelledError:
                break
            try:
                await self._process_issue(project_id, issue_id)
            finally:
                self.queue.task_done()

    async def enqueue(self, project_id: str, issue_id: str) -> None:
        await self.queue.put((project_id, issue_id))

    async def update_embeddings(self, project_id: str) -> None:
        """Update embeddings for a specific project."""
        await self.embedding_manager.update_project_embeddings(project_id)

    async def process_webhook_payload(self, jira_issue_payload: dict) -> None:
        """Process a complete Jira issue payload directly."""
        # Extract issue information from Jira issue payload
        issue_data = jira_issue_payload.get("issue", {})
        issue_key = issue_data.get("key")
        project_key = issue_data.get("fields", {}).get("project", {}).get("key")
        
        if not issue_key or not project_key:
            raise ValueError("Could not extract issue key or project key from Jira issue payload")
        
        # Extract issue type and status from Jira issue data
        issue_type = issue_data.get("fields", {}).get("issuetype", {}).get("name")
        status = issue_data.get("fields", {}).get("status", {}).get("name")
        
        if not issue_type or not status:
            raise ValueError("Could not extract issue type or status from Jira issue payload")
        
        # Find the appropriate agent for this issue type and status
        agent_type = self.config.find_agent(project_key, issue_type, status)
        if not agent_type:
            return  # No agent configured for this combination
        
        agent_cls = AGENT_REGISTRY.get(agent_type)
        if not agent_cls:
            return  # Agent type not found in registry
        
        # Extract issue content from Jira issue data
        fields = issue_data.get("fields", {})
        issue_description = fields.get("description", "") or ""
        issue_summary = fields.get("summary", "") or ""
        query = f"{issue_summary} {issue_description}"
        
        # Get relevant context from embeddings
        context = self.embedding_manager.get_relevant_context(project_key, query)
        
        # Prepare issue data with context
        issue_dict = {
            "description": issue_description,
            "summary": issue_summary,
            "context": context
        }
        
        # Evaluate the issue
        agent = agent_cls()
        result: EvaluationResult = agent.evaluate(issue_dict)
        
        # Apply the evaluation result
        self.jira.add_comment(issue_key, result.comment)
        if result.new_status:
            self.jira.transition(issue_key, result.new_status)

    async def _process_issue(self, project_id: str, issue_id: str) -> None:
        issue = self.jira.fetch_issue(issue_id)
        issue_type = issue.fields.issuetype.name
        status = issue.fields.status.name

        agent_type = self.config.find_agent(project_id, issue_type, status)
        if not agent_type:
            return

        agent_cls = AGENT_REGISTRY.get(agent_type)
        if not agent_cls:
            return

        # Get relevant context from embeddings
        issue_description = getattr(issue.fields, "description", "") or ""
        issue_summary = getattr(issue.fields, "summary", "") or ""
        query = f"{issue_summary} {issue_description}"
        
        context = self.embedding_manager.get_relevant_context(project_id, query)
        
        # Prepare issue data with context
        issue_dict = {
            "description": issue_description,
            "summary": issue_summary,
            "context": context
        }
        
        agent = agent_cls()
        result: EvaluationResult = agent.evaluate(issue_dict)
        self.jira.add_comment(issue_id, result.comment)
        if result.new_status:
            self.jira.transition(issue_id, result.new_status)
