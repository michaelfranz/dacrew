from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML required at runtime
    yaml = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv is optional
    pass


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
    token: str = ""
    webhook_secret: str = ""


@dataclass
class CodebaseConfig:
    """Configuration for a codebase repository."""

    repo: str
    include_patterns: List[str] = field(default_factory=lambda: ["**/*"])
    exclude_patterns: List[str] = field(default_factory=lambda: ["node_modules/**", "build/**", ".git/**"])
    branch: str = "main"
    update_frequency_hours: int = 24


@dataclass
class DocumentsConfig:
    """Configuration for documentation sources."""

    paths: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    update_frequency_hours: int = 168  # 1 week


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation and storage."""

    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    workspace_path: str = "./embeddings"
    max_workers: int = 4


@dataclass
class ProjectConfig:
    """Configuration for a single Jira project."""

    project_id: str
    type_status_map: Dict[str, Dict[str, str]] = field(default_factory=dict)
    codebase: Optional[CodebaseConfig] = None
    documents: Optional[DocumentsConfig] = None
    embedding: Optional[EmbeddingConfig] = None


@dataclass
class AppConfig:
    """Top level application configuration."""

    jira: JiraConfig
    projects: List[ProjectConfig] = field(default_factory=list)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    @staticmethod
    def load(path: str | Path) -> "AppConfig":
        """Load configuration from a YAML file."""

        data = _load_file(path)
        jira_data = data["jira"].copy()
        
        # Always load sensitive data from environment variables (never from config file)
        jira_data["token"] = os.getenv("JIRA_API_TOKEN", "")
        jira_data["webhook_secret"] = os.getenv("JIRA_WEBHOOK_SECRET", "")
        
        jira = JiraConfig(**jira_data)
        
        # Load global embedding config
        embedding_data = data.get("embedding", {})
        embedding = EmbeddingConfig(**embedding_data)
        
        projects = []
        for p in data.get("projects", []):
            project_id = p["project_id"]
            type_status_map = p.get("type_status_map", {})
            
            # Load codebase config if present
            codebase = None
            if "codebase" in p:
                codebase = CodebaseConfig(**p["codebase"])
            
            # Load documents config if present
            documents = None
            if "documents" in p:
                documents = DocumentsConfig(**p["documents"])
            
            # Load project-specific embedding config if present
            project_embedding = None
            if "embedding" in p:
                project_embedding = EmbeddingConfig(**p["embedding"])
            
            project = ProjectConfig(
                project_id=project_id,
                type_status_map=type_status_map,
                codebase=codebase,
                documents=documents,
                embedding=project_embedding,
            )
            projects.append(project)
        
        return AppConfig(jira=jira, projects=projects, embedding=embedding)

    def find_agent(self, project_id: str, issue_type: str, status: str) -> Optional[str]:
        """Return the agent type for the given project, issue type and status."""

        for project in self.projects:
            if project.project_id == project_id:
                return project.type_status_map.get(issue_type, {}).get(status)
        return None

    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """Return the project configuration for the given project ID."""
        
        for project in self.projects:
            if project.project_id == project_id:
                return project
        return None
