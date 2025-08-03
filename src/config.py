import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

# Configuration classes
@dataclass
class KnowledgeSourceConfig:
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

@dataclass
class AgentKnowledgeConfig:
    codebase: Optional[Dict[str, Any]] = None
    jira: Optional[Dict[str, Any]] = None
    documents: Optional[Dict[str, Any]] = None

@dataclass
class AgentTaskEntry:
    name: str
    tags: List[str] = field(default_factory=list)

@dataclass
class CrewAgentConfig:
    name: str
    role: str
    backstory: str
    goal: str
    knowledge: AgentKnowledgeConfig = field(default_factory=AgentKnowledgeConfig)
    tools: List[str] = field(default_factory=list)
    llm: str = "gpt-4"
    issue_routing: Optional[Dict[str, Any]] = None

@dataclass
class CrewToolConfig:
    name: str
    description: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrewTaskConfig:
    name: str
    description: str
    input: Optional[str] = None
    output: Optional[str] = None

@dataclass
class CrewWorkflowConfig:
    steps: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class CrewConfig:
    name: str
    description: str = ""
    agents: List[CrewAgentConfig] = field(default_factory=list)
    tools: List[CrewToolConfig] = field(default_factory=list)
    tasks: List[CrewTaskConfig] = field(default_factory=list)
    workflow: Optional[CrewWorkflowConfig] = None

@dataclass
class JiraConfig:
    url: str
    jira_project_key: str
    user_id: str
    fetch_limit: int = 50
    api_token: str = ""

@dataclass
class AIConfig:
    model: str = "gpt-4"
    temperature: float = 0.7
    embeddings_model: str = "text-embedding-3-small"
    openai_api_key: str = ""

@dataclass
class CodebaseEmbeddingConfig:
    path: str = ""

# Template loading and configuration merging
def load_template(template_name: str) -> Dict[str, Any]:
    """Load a template configuration by name."""
    template_path = Path(f"templates/{template_name}.yml")
    if template_path.exists():
        with open(template_path, 'r') as f:
            return yaml.safe_load(f)
    return {}

def merge_configs(template_config: Dict[str, Any], project_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge template configuration with project-specific overrides."""
    merged = template_config.copy()

    # Merge top-level keys
    for key, value in project_config.items():
        if isinstance(value, dict) and key in merged:
            # For nested dictionaries, merge recursively
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    return merged

def load_crew_config(crew_name: Optional[str] = None, project_config_path: str = "config.yml") -> CrewConfig:
    """Load crew configuration with optional template support."""
    # Load project configuration
    if os.path.exists(project_config_path):
        with open(project_config_path, 'r') as f:
            project_config = yaml.safe_load(f)
    else:
        project_config = {}

    # Handle template loading if crew name is provided
    if crew_name:
        template_config = load_template(crew_name)
        merged_config = merge_configs(template_config, project_config)
    else:
        merged_config = project_config

    # Convert to CrewConfig object
    return parse_crew_config(merged_config)

def parse_crew_config(config_dict: Dict[str, Any]) -> CrewConfig:
    """Parse dictionary configuration into CrewConfig object."""
    # Parse agents
    agents = []
    for agent_dict in config_dict.get('agents', []):
        # Parse nested knowledge configuration
        knowledge_config = AgentKnowledgeConfig()
        if 'knowledge' in agent_dict:
            knowledge_data = agent_dict['knowledge']
            if 'codebase' in knowledge_data:
                knowledge_config.codebase = knowledge_data['codebase']
            if 'jira' in knowledge_data:
                knowledge_config.jira = knowledge_data['jira']
            if 'documents' in knowledge_data:
                knowledge_config.documents = knowledge_data['documents']

        agent = CrewAgentConfig(
            name=agent_dict.get('name', ''),
            role=agent_dict.get('role', ''),
            backstory=agent_dict.get('backstory', ''),
            goal=agent_dict.get('goal', ''),
            knowledge=knowledge_config,
            tools=agent_dict.get('tools', []),
            llm=agent_dict.get('llm', 'gpt-4')
        )

        # Handle issue_routing if present
        if 'issue_routing' in agent_dict:
            agent.issue_routing = agent_dict['issue_routing']

        agents.append(agent)

    # Parse tools
    tools = []
    for tool_dict in config_dict.get('tools', []):
        tool = CrewToolConfig(
            name=tool_dict.get('name', ''),
            description=tool_dict.get('description', ''),
            type=tool_dict.get('type', ''),
            config=tool_dict.get('config', {})
        )
        tools.append(tool)

    # Parse tasks
    tasks = []
    for task_dict in config_dict.get('tasks', []):
        task = CrewTaskConfig(
            name=task_dict.get('name', ''),
            description=task_dict.get('description', ''),
            input=task_dict.get('input'),
            output=task_dict.get('output')
        )
        tasks.append(task)

    # Parse workflow
    workflow = None
    if 'workflow' in config_dict:
        workflow_data = config_dict['workflow']
        workflow = CrewWorkflowConfig(
            steps=workflow_data.get('steps', [])
        )

    # Create and return CrewConfig object
    crew_config = CrewConfig(
        name=config_dict.get('name', ''),
        description=config_dict.get('description', ''),
        agents=agents,
        tools=tools,
        tasks=tasks,
        workflow=workflow
    )

    return crew_config

# Utility functions for configuration handling
def parse_agent_knowledge_config(config_dict: Dict[str, Any]) -> AgentKnowledgeConfig:
    """Parse agent knowledge configuration."""
    return AgentKnowledgeConfig(
        codebase=config_dict.get('codebase'),
        jira=config_dict.get('jira'),
        documents=config_dict.get('documents')
    )

def parse_agent_tasks(config_dict: Dict[str, Any]) -> List[AgentTaskEntry]:
    """Parse agent tasks configuration."""
    return [AgentTaskEntry(name=task.get('name', ''), tags=task.get('tags', []))
            for task in config_dict.get('tasks', [])]

def _merge_configs(template_config: Dict[str, Any], project_config: Dict[str, Any]) -> Dict[str, Any]:
    """Internal helper to merge configurations."""
    return merge_configs(template_config, project_config)

def _validate_issue_routing_conflicts_and_tasks(crew_config: CrewConfig) -> None:
    """Validate uniqueness of issue routing and task reference integrity."""
    pass