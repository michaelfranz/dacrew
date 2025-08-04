import asyncio
import sys
import types

import pytest

from dacrew.config import AppConfig, JiraConfig


class DummyJiraClient:
    def __init__(self, cfg: JiraConfig):
        pass

    def fetch_issue(self, issue_id: str):
        raise NotImplementedError

    def add_comment(self, issue_id: str, comment: str) -> None:
        raise NotImplementedError

    def transition(self, issue_id: str, status_name: str) -> None:
        raise NotImplementedError


def test_service_start_stop(monkeypatch):
    monkeypatch.setitem(sys.modules, 'crewai', types.SimpleNamespace(Agent=object))
    monkeypatch.setitem(sys.modules, 'jira', types.SimpleNamespace(JIRA=object))
    from dacrew.service import EvaluationService
    monkeypatch.setattr('dacrew.service.JiraClient', DummyJiraClient)

    cfg = AppConfig(jira=JiraConfig(url='u', user_id='u', token='t'), projects=[])
    service = EvaluationService(cfg)

    async def run() -> None:
        service.start()
        assert service.worker_task is not None
        await asyncio.sleep(0)
        await service.stop()
        assert service.worker_task.done()

    asyncio.run(run())
