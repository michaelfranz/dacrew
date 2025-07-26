"""Configuration management for DaCrew - AI-powered Development Crew"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml
from pydantic import SecretStr


@dataclass
class JiraConfig:
    """Jira connection configuration"""
    url: str
    jira_project_key: str
    user_id: str
    api_token: str = ""   # From global config only


@dataclass
class AIConfig:
    """AI/LLM configuration"""
    model: str = "gpt-4"
    temperature: float = 0.7
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_api_key: SecretStr = SecretStr("")  # From global config only


# ------------------------------
# Embedding Configs
# ------------------------------
@dataclass
class CodebaseEmbeddingConfig:
    path: str = "./"
    include_patterns: List[str] = field(default_factory=lambda: ["src/**/*.java", "src/**/*.py"])
    exclude_patterns: List[str] = field(default_factory=lambda: ["node_modules/**", "build/**"])


@dataclass
class IssuesEmbeddingConfig:
    include_statuses: List[str] = field(default_factory=lambda: ["To Do", "In Progress", "Done"])
    exclude_statuses: List[str] = field(default_factory=lambda: ["Deleted", "Archived"])


@dataclass
class DocumentsEmbeddingConfig:
    paths: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)


@dataclass
class EmbeddingConfig:
    codebase: CodebaseEmbeddingConfig = field(default_factory=CodebaseEmbeddingConfig)
    issues: IssuesEmbeddingConfig = field(default_factory=IssuesEmbeddingConfig)
    documents: DocumentsEmbeddingConfig = field(default_factory=DocumentsEmbeddingConfig)


@dataclass
class CommandsConfig:
    build: str = "./gradlew build"
    test: str = "./gradlew test"


@dataclass
class GitConfig:
    default_branch_prefix: str = "feature/"
    commit_template: str = "Implementing {ISSUE_ID}: {ISSUE_TITLE}"


@dataclass
class Config:
    """Main configuration container"""
    project: str
    embedding: EmbeddingConfig
    jira: JiraConfig
    ai: AIConfig
    commands: CommandsConfig
    git: GitConfig
    config_file: Path

    @classmethod
    def load(cls, project_root: Path = Path.cwd()) -> 'Config':
        global_config_path = Path.home() / ".dacrew" / "config.yml"
        project_config_path = project_root / ".dacrew.yml"

        if not global_config_path.exists():
            raise FileNotFoundError(
                f"Global config not found at {global_config_path}. "
                "Run 'dacrew init' to create one."
            )

        global_config = cls._load_yaml(global_config_path)
        project_config = cls._load_yaml(project_config_path) if project_config_path.exists() else {}

        if project_config:
            cls._validate_project_config(project_config)

        merged = _merge_configs(global_config, project_config)

        if "project" not in merged:
            raise ValueError("❌ The 'project' key must be defined in the project config (.dacrew.yml).")

        jira_conf = merged.get("jira", {})
        ai_conf = merged.get("ai", {})
        embedding_conf = merged.get("embedding", {})
        gen_conf = merged.get("gen", {})
        git_conf = merged.get("git", {})

        return cls(
            project=merged["project"],
            embedding=EmbeddingConfig(
                codebase=CodebaseEmbeddingConfig(
                    path=embedding_conf.get("codebase", {}).get("path", "./"),
                    include_patterns=embedding_conf.get("codebase", {}).get("include_patterns", ["src/**/*.java", "src/**/*.py"]),
                    exclude_patterns=embedding_conf.get("codebase", {}).get("exclude_patterns", ["node_modules/**", "build/**"]),
                ),
                issues=IssuesEmbeddingConfig(
                    include_statuses=embedding_conf.get("issues", {}).get("include_statuses", ["To Do", "In Progress", "Done"]),
                    exclude_statuses=embedding_conf.get("issues", {}).get("exclude_statuses", ["Deleted", "Archived"]),
                ),
                documents=DocumentsEmbeddingConfig(
                    paths=embedding_conf.get("documents", {}).get("paths", []),
                    urls=embedding_conf.get("documents", {}).get("urls", []),
                ),
            ),
            jira=JiraConfig(
                url=jira_conf.get("url", ""),
                jira_project_key=jira_conf.get("jira_project_key", ""),
                user_id=jira_conf.get("user_id", ""),
                api_token=jira_conf.get("api_token", "")  # global only
            ),
            ai=AIConfig(
                model=ai_conf.get("model", "gpt-4"),
                temperature=float(ai_conf.get("temperature", 0.7)),
                embeddings_model=ai_conf.get("embeddings_model", "sentence-transformers/all-MiniLM-L6-v2"),
                openai_api_key=ai_conf.get("openai_api_key", "")
            ),
            commands=CommandsConfig(
                build=gen_conf.get("build", "./gradlew build"),
                test=gen_conf.get("test", "./gradlew test")
            ),
            git=GitConfig(
                default_branch_prefix=git_conf.get("default_branch_prefix", "feature/"),
                commit_template=git_conf.get("commit_template", "Implementing {ISSUE_ID}: {ISSUE_TITLE}")
            ),
            config_file=project_config_path if project_config_path.exists() else global_config_path
        )

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _validate_project_config(project_config: dict):
        """Ensure forbidden keys (secrets) are not defined in project config."""
        forbidden_keys = [
            ("ai", "openai_api_key"),
            ("jira", "api_token"),
        ]
        for section, key in forbidden_keys:
            section_data = project_config.get(section) or {}
            if key in section_data:
                raise ValueError(
                    f"❌ '{section}.{key}' must NOT be defined in project config (.dacrew.yml). "
                    f"Move it to ~/.dacrew/config.yml instead."
                )


def _merge_configs(global_config: dict, project_config: dict) -> dict:
    """
    Merge global and project configs.
    Project config overrides global config except for secret keys.
    """
    merged = global_config.copy()

    def deep_merge(base, override):
        for k, v in override.items():
            if v is None:
                continue
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                deep_merge(base[k], v)
            else:
                if (k == "openai_api_key" and "ai" in base) or (k == "api_token" and "jira" in base):
                    continue
                base[k] = v
        return base

    return deep_merge(merged, project_config)