from __future__ import annotations

import asyncio
from typing import Dict, Type

from .agents.base import EvaluationResult, BaseAgent
from .agents.ready import ReadyForDevelopmentEvaluator
from .agents.todo import TodoEvaluator
from .config import AppConfig
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

        agent = agent_cls()
        issue_dict = {"description": getattr(issue.fields, "description", "")}
        result: EvaluationResult = agent.evaluate(issue_dict)
        self.jira.add_comment(issue_id, result.comment)
        if result.new_status:
            self.jira.transition(issue_id, result.new_status)
