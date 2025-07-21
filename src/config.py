"""Configuration management for DaCrew - AI-powered Development Crew"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class JiraConfig:
    """Jira connection configuration"""
    url: str
    username: str
    api_token: str

    @classmethod
    def from_env(cls) -> 'JiraConfig':
        return cls(
            url=os.getenv('JIRA_URL', ''),
            username=os.getenv('JIRA_USERNAME', ''),
            api_token=os.getenv('JIRA_API_TOKEN', '')
        )


@dataclass
class AIConfig:
    """AI/LLM configuration"""
    openai_api_key: str
    model: str
    temperature: float
    embeddings_model: str
    chroma_persist_directory: str

    @classmethod
    def from_env(cls) -> 'AIConfig':
        return cls(
            openai_api_key=os.getenv('OPENAI_API_KEY', ''),
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            embeddings_model=os.getenv('EMBEDDINGS_MODEL', 'all-MiniLM-L6-v2'),
            chroma_persist_directory=os.getenv('CHROMA_PERSIST_DIRECTORY', './data/chroma_db')
        )


@dataclass
class ProjectConfig:
    """Project context configuration"""
    default_project_key: str
    default_user_id: str

    @classmethod
    def from_env(cls) -> 'ProjectConfig':
        return cls(
            default_project_key=os.getenv('DEFAULT_PROJECT_KEY', ''),
            default_user_id=os.getenv('DEFAULT_USER_ID', '')
        )


@dataclass
class Config:
    """Main configuration container"""
    jira: JiraConfig
    ai: AIConfig
    project: ProjectConfig
    config_file: str = ".env"  # Add config file path for display

    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment variables"""
        # Determine which .env file was loaded
        env_file = ".env"
        if not Path(env_file).exists():
            env_file = ".env.example"
        if not Path(env_file).exists():
            env_file = "environment variables"

        return cls(
            jira=JiraConfig.from_env(),
            ai=AIConfig.from_env(),
            project=ProjectConfig.from_env(),
            config_file=env_file
        )