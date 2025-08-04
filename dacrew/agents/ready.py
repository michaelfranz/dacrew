from __future__ import annotations

from crewai import Agent

from .base import BaseAgent, EvaluationResult


class ReadyForDevelopmentEvaluator(BaseAgent):
    """Confirm that an issue is ready for development."""

    def __init__(self) -> None:
        self.agent = Agent(
            role="ready-for-development-evaluator",
            goal="Confirm that the issue is actionable by developers",
            backstory="Ensures backlog items meet the team's definition of ready.",
        )

    def evaluate(self, issue: dict) -> EvaluationResult:
        description = issue.get("description", "").strip()
        if description:
            comment = "Issue is confirmed ready for development."
        else:
            comment = (
                "Issue is missing information even though it's marked ready; "
                "please update the description."
            )
        return EvaluationResult(comment=comment, new_status=None)
