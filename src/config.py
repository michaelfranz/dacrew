"""Configuration management for DaCrew - AI-powered Development Crew"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml
from pydantic import SecretStr

# ------------------------------
# Crew Configuration
# ------------------------------

@dataclass
class KnowledgeSourceConfig:
    enabled: bool = False
    tags: List[str] = field(default_factory=list)

@dataclass
class AgentKnowledgeConfig:
    codebase: KnowledgeSourceConfig = field(default_factory=KnowledgeSourceConfig)
    jira: KnowledgeSourceConfig = field(default_factory=KnowledgeSourceConfig)
    documents: KnowledgeSourceConfig = field(default_factory=KnowledgeSourceConfig)

@dataclass
class AgentTaskEntry:
    name: str
    tags: List[str] = field(default_factory=list)

@dataclass
class AgentKnowledgeConfig:
    codebase: KnowledgeSourceConfig = field(default_factory=KnowledgeSourceConfig)
    jira: KnowledgeSourceConfig = field(default_factory=KnowledgeSourceConfig)
    documents: KnowledgeSourceConfig = field(default_factory=KnowledgeSourceConfig)

@dataclass
class CrewAgentConfig:
    name: str
    role: str
    backstory: str
    goal: str
    knowledge: AgentKnowledgeConfig = field(default_factory=AgentKnowledgeConfig)
    tools: List[str] = field(default_factory=list)
    llm: str = "gpt-4"
    issue_routing: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
@dataclass
class CrewToolConfig:
    name: str
    description: str
    type: str
    config: dict = field(default_factory=dict)

@dataclass
class CrewTaskConfig:
    name: str
    description: str
    input: Optional[str] = None
    output: Optional[str] = None

@dataclass
class CrewWorkflowConfig:
    steps: List[str] = field(default_factory=list)

@dataclass
class CrewConfig:
    name: str
    description: str
    agents: List[CrewAgentConfig] = field(default_factory=list)
    tools: List[CrewToolConfig] = field(default_factory=list)
    tasks: List[CrewTaskConfig] = field(default_factory=list)
    workflow: CrewWorkflowConfig = field(default_factory=CrewWorkflowConfig)

@dataclass
class JiraConfig:
    """Jira connection configuration"""
    url: str
    jira_project_key: str
    user_id: str
    fetch_limit: int = 500
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
    include_statuses: List[str] = field(default_factory=lambda: None)
    exclude_statuses: List[str] = field(default_factory=lambda: ["Cancelled"])

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
    crew: Optional[CrewConfig] = None  # Added crew section

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
        crew_conf = merged.get("crew")

        # Parse crew section
        crew = None
        if crew_conf:
            crew = CrewConfig(
                name=crew_conf.get("name", "default_crew"),
                description=crew_conf.get("description", ""),
                agents=[
                    CrewAgentConfig(
                        name=a.get("name"),
                        role=a.get("role", ""),
                        backstory=a.get("backstory", ""),
                        goal=a.get("goal", ""),
                        knowledge=parse_agent_knowledge_config(a.get("knowledge")),
                        tools=a.get("tools", []),
                        llm=a.get("llm", "gpt-4"),
                        issue_routing=a.get("issue_routing", {})
                    )
                    for a in crew_conf.get("agents", [])
                ],
                tools=[CrewToolConfig(**t) for t in crew_conf.get("tools", [])],
                tasks=[CrewTaskConfig(**tsk) for tsk in crew_conf.get("tasks", [])],
                workflow=CrewWorkflowConfig(
                    steps=crew_conf.get("workflow", {}).get("steps", [])
                ),
            )
            _validate_issue_routing_conflicts_and_tasks(
                agents=crew.agents,
                defined_tasks=crew.tasks
            )

        return cls(
            project=merged["project"],
            embedding=EmbeddingConfig(
                codebase=CodebaseEmbeddingConfig(
                    path=embedding_conf.get("codebase", {}).get("path", "./"),
                    include_patterns=embedding_conf.get("codebase", {}).get("include_patterns", ["src/**/*.java", "src/**/*.py"]),
                    exclude_patterns=embedding_conf.get("codebase", {}).get("exclude_patterns", ["node_modules/**", "build/**"]),
                ),
                issues=IssuesEmbeddingConfig(
                    include_statuses=embedding_conf.get("issues", {}).get("include_statuses", []),
                    exclude_statuses=embedding_conf.get("issues", {}).get("exclude_statuses", ["Cancelled"]),
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
                api_token=jira_conf.get("api_token", "")
            ),
            ai=AIConfig(
                model=ai_conf.get("model", "gpt-4"),
                temperature=float(ai_conf.get("temperature", 0.7)),
                embeddings_model=ai_conf.get("embeddings_model", "sentence-transformers/all-MiniLM-L6-v2"),
                openai_api_key=SecretStr(ai_conf.get("openai_api_key", ""))
            ),
            commands=CommandsConfig(
                build=gen_conf.get("build", "./gradlew build"),
                test=gen_conf.get("test", "./gradlew test")
            ),
            git=GitConfig(
                default_branch_prefix=git_conf.get("default_branch_prefix", "feature/"),
                commit_template=git_conf.get("commit_template", "Implementing {ISSUE_ID}: {ISSUE_TITLE}")
            ),
            config_file=project_config_path if project_config_path.exists() else global_config_path,
            crew=crew
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

def parse_agent_knowledge_config(raw: Optional[Dict[str, Any]]) -> AgentKnowledgeConfig:
    def parse_source(source: Optional[Dict[str, Any]]) -> KnowledgeSourceConfig:
        if not source:
            return KnowledgeSourceConfig()
        return KnowledgeSourceConfig(
            enabled=source.get("enabled", False),
            tags=source.get("tags", [])
        )

    if raw is None:
        return AgentKnowledgeConfig()

    return AgentKnowledgeConfig(
        codebase=parse_source(raw.get("codebase")),
        jira=parse_source(raw.get("jira")),
        documents=parse_source(raw.get("documents"))
    )

def parse_agent_tasks(raw: Dict[str, Any]) -> Dict[str, Dict[str, AgentTaskEntry]]:
    tasks = {}
    for issue_type, statuses in raw.items():
        tasks[issue_type] = {}
        for status, val in statuses.items():
            tasks[issue_type][status] = AgentTaskEntry(
                name=val.get("name"),
                tags=val.get("tags", [])
            )
    return tasks

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

def _validate_issue_routing_conflicts_and_tasks(
        agents: List[CrewAgentConfig],
        defined_tasks: List[CrewTaskConfig]
):
    """Validate uniqueness of issue routing and task reference integrity."""
    seen_routes = {}  # (issue_type, status) -> agent_name
    defined_task_names = {task.name for task in defined_tasks}

    for agent in agents:
        for issue_type, status_map in agent.issue_routing.items():
            for status, route in status_map.items():
                key = (issue_type, status)

                # Check for duplicate routes
                if key in seen_routes:
                    other_agent = seen_routes[key]
                    raise ValueError(
                        f"❌ Conflict in issue_routing: Issue type '{issue_type}' with status '{status}' "
                        f"is defined in both agent '{agent.name}' and agent '{other_agent}'."
                    )
                seen_routes[key] = agent.name

                # Check task existence
                task_name = route.get("name")
                if task_name not in defined_task_names:
                    raise ValueError(
                        f"❌ Undefined task: Agent '{agent.name}' refers to task '{task_name}' "
                        f"in issue_routing for type '{issue_type}' and status '{status}', "
                        f"but this task is not defined in the top-level 'tasks' section."
                    )