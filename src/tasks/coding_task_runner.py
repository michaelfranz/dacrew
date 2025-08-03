"""Task runner for coding tasks with pre/post git actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import subprocess

from rich import Console

from config import Config, CrewAgentConfig
from codebase import SimpleCodebaseManager
from .base_task_runner import BaseTaskRunner


console = Console()
config = Config.load()


class CodingTaskRunner(BaseTaskRunner):
    """Extends ``BaseTaskRunner`` with git pre/post actions."""

    def __init__(
        self,
        agent_config: CrewAgentConfig,
        *,
        auto_commit: bool = False,
        auto_push: bool = False,
    ) -> None:
        super().__init__(config, agent_config)
        self.auto_commit = auto_commit
        self.auto_push = auto_push
        self.repo_path: Path | None = None
        self.branch_name: str | None = None
        self.codebase_manager = SimpleCodebaseManager()

    def _derive_branch_name(self, issue_data: dict[str, Any]) -> str:
        """Create a branch name from issue key and summary."""
        key = issue_data.get("key") or issue_data.get("id") or "issue"
        summary = issue_data.get("summary", "").lower().replace(" ", "-").replace("/", "-")
        return f"feature/{key}-{summary}" if summary else f"feature/{key}"

    def _pre_agent_action(self, issue_data: dict[str, Any]):
        """Ensure repository exists and create working branch."""
        repo_info = self.codebase_manager.get_current_repository_info()
        if not repo_info:
            console.print("⚠️ No active repository configured", style="yellow")
            return

        repo_url = repo_info.get("repo_url")
        repo_path = Path(repo_info.get("actual_path", "."))
        base_branch = repo_info.get("branch", "main")

        # Clone if missing, otherwise pull latest changes
        if repo_path.exists():
            console.print(f"📥 Updating repository at {repo_path}", style="blue")
            subprocess.run(["git", "-C", str(repo_path), "pull"], check=False)
        else:
            console.print(f"📥 Cloning repository from {repo_url} to {repo_path}", style="blue")
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", repo_url, str(repo_path)], check=True)

        # Switch to base branch and update
        subprocess.run(["git", "-C", str(repo_path), "checkout", base_branch], check=False)
        subprocess.run(["git", "-C", str(repo_path), "pull", "origin", base_branch], check=False)

        # Create feature branch
        branch_name = self._derive_branch_name(issue_data)
        result = subprocess.run(
            ["git", "-C", str(repo_path), "checkout", "-b", branch_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Branch may already exist; try to check it out
            subprocess.run([
                "git",
                "-C",
                str(repo_path),
                "checkout",
                branch_name,
            ], check=False)

        self.repo_path = repo_path
        self.branch_name = branch_name

    def _post_agent_action(self, issue_data: dict[str, Any]):
        """Stage, commit, and optionally push code changes."""
        if not self.repo_path:
            return

        repo_path = self.repo_path
        subprocess.run(["git", "-C", str(repo_path), "add", "."], check=False)

        if self.auto_commit:
            message = (
                f"{issue_data.get('key', '')}: {issue_data.get('summary', '').strip()}"
            )
            commit = subprocess.run(
                ["git", "-C", str(repo_path), "commit", "-m", message],
                capture_output=True,
                text=True,
            )
            if commit.returncode == 0 and self.auto_push and self.branch_name:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repo_path),
                        "push",
                        "-u",
                        "origin",
                        self.branch_name,
                    ],
                    check=False,
                )
