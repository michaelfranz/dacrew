from __future__ import annotations

from fastapi import FastAPI

from .config import AppConfig
from .service import EvaluationService


def create_app(config_path: str = "config.yml") -> FastAPI:
    """Create and configure the FastAPI application."""

    cfg = AppConfig.load(config_path)
    service = EvaluationService(cfg)

    app = FastAPI(title="dacrew")

    @app.on_event("startup")
    async def _start_service() -> None:
        service.start()

    @app.on_event("shutdown")
    async def _stop_service() -> None:
        await service.stop()

    @app.post("/evaluate/{project_id}/{issue_id}")
    async def evaluate(project_id: str, issue_id: str) -> dict[str, str]:
        await service.enqueue(project_id, issue_id)
        return {"status": "queued"}

    return app


app = create_app()
