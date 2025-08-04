from __future__ import annotations

from fastapi import FastAPI

from .config import AppConfig
from .service import EvaluationService


def create_app(config_path: str = "config.json") -> FastAPI:
    """Create and configure the FastAPI application."""

    cfg = AppConfig.load(config_path)
    service = EvaluationService(cfg)

    app = FastAPI(title="dacrew")

    @app.post("/evaluate/{project_id}/{issue_id}")
    async def evaluate(project_id: str, issue_id: str) -> dict[str, str]:
        await service.enqueue(project_id, issue_id)
        return {"status": "queued"}

    return app


app = create_app()
