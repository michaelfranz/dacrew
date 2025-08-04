from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML required at runtime
    yaml = None


def _load_file(path: str | Path) -> dict:
    if yaml is None:  # pragma: no cover - dependency check
        raise RuntimeError("PyYAML is required to load configuration files")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class JiraConfig:
    """Settings required to connect to Jira."""

    url: str
    user_id: str
    token: str


@dataclass
class ProjectConfig:
    """Configuration for a single Jira project."""

    project_id: str
    type_status_map: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class AppConfig:
    """Top level application configuration."""

    jira: JiraConfig
    projects: List[ProjectConfig] = field(default_factory=list)

    @staticmethod
    def load(path: str | Path) -> "AppConfig":
        """Load configuration from a YAML file."""

        data = _load_file(path)
        jira = JiraConfig(**data["jira"])
        projects = [
            ProjectConfig(
                project_id=p["project_id"],
                type_status_map=p.get("type_status_map", {}),
            )
            for p in data.get("projects", [])
        ]
        return AppConfig(jira=jira, projects=projects)

    def find_agent(self, project_id: str, issue_type: str, status: str) -> Optional[str]:
        """Return the agent type for the given project, issue type and status."""

        for project in self.projects:
            if project.project_id == project_id:
                return project.type_status_map.get(issue_type, {}).get(status)
        return None
