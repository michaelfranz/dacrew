from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class EvaluationResult:
    """Result returned by an evaluation agent."""

    comment: str
    new_status: Optional[str] = None


class BaseAgent:
    """Base class for all evaluation agents."""

    def evaluate(self, issue: dict) -> EvaluationResult:
        raise NotImplementedError
