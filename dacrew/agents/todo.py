from __future__ import annotations

from crewai import Agent

from .base import BaseAgent, EvaluationResult


class TodoEvaluator(BaseAgent):
    """Evaluate bugs that are in the "To Do" state."""

    def __init__(self) -> None:
        self.agent = Agent(
            role="todo-evaluator",
            goal="Assess if the bug description is clear enough to be worked on",
            backstory="Specialist in analysing early stage bug reports.",
        )

    def evaluate(self, issue: dict) -> EvaluationResult:
        """Very small placeholder implementation.

        A real implementation would craft a Crew task and let the agent
        reason about the provided issue using an LLM. Here we simply check
        if a description is present.
        """

        description = issue.get("description", "").strip()
        if description:
            comment = "Issue description looks sufficient for development."
            new_status = "Ready for Development"
        else:
            comment = (
                "The issue description is missing. Please provide details on how to"
                " reproduce the bug and its impact."
            )
            new_status = None
        return EvaluationResult(comment=comment, new_status=new_status)
