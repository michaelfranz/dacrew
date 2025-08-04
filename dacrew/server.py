from __future__ import annotations

import os
from fastapi import FastAPI

from .config import AppConfig
from .service import EvaluationService


def create_app(config_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    The configuration file path can be provided explicitly or through the
    ``DACREW_CONFIG`` environment variable. If neither is supplied, the
    application defaults to ``config.yml`` in the working directory.
    """

    path = config_path or os.environ.get("DACREW_CONFIG", "config.yml")
    cfg = AppConfig.load(path)
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
