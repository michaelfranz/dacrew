# tests/unit/test_config.py

import tempfile
import shutil
from pathlib import Path
import pytest
import yaml

from src.config import Config


@pytest.fixture
def temp_config_dir():
    """Creates a temporary config directory to simulate ~/.dacrew and a project root."""
    temp_home = Path(tempfile.mkdtemp())
    dacrew_dir = temp_home / ".dacrew"
    dacrew_dir.mkdir(parents=True)

    project_root = temp_home / "my_project"
    project_root.mkdir(parents=True)

    yield dacrew_dir, project_root

    # Cleanup after test
    shutil.rmtree(temp_home)


def write_yaml(path: Path, content: dict):
    path.write_text(yaml.dump(content))


def test_load_config_with_global_and_project(temp_config_dir, monkeypatch):
    dacrew_dir, project_root = temp_config_dir
    monkeypatch.setattr(Path, "home", lambda: dacrew_dir.parent)
    global_config_path = dacrew_dir / "config.yml"
    project_config_path = project_root / ".dacrew.yml"

    global_config = {
        "jira": {
            "url": "https://global-jira.atlassian.net",
            "username": "global_user",
            "api_token": "global_token"
        },
        "ai": {
            "openai_api_key": "global-key",
            "model": "gpt-4",
            "temperature": 0.5
        }
    }
    project_config = {
        "project": "my-project",
        "jira": {
            "url": "https://project-jira.atlassian.net"
        },
        "commands": {
            "build": "./gradlew customBuild",
            "test": "./gradlew customTest"
        }
    }

    write_yaml(global_config_path, global_config)
    write_yaml(project_config_path, project_config)

    config = Config.load(project_root=project_root)

    assert config.project == "my-project"
    assert config.jira.url == "https://project-jira.atlassian.net"  # Project overrides global
    assert config.jira.username == "global_user"
    assert config.commands.build == "./gradlew customBuild"
    assert config.ai.model == "gpt-4"


def test_missing_project_key_raises_error(temp_config_dir):
    dacrew_dir, project_root = temp_config_dir
    global_config_path = dacrew_dir / "config.yml"
    write_yaml(global_config_path, {
        "jira": {"url": "https://example.com", "username": "user", "api_token": "token"},
        "ai": {"openai_api_key": "key"}
    })

    with pytest.raises(ValueError, match="The 'project' key must be defined"):
        Config.load(project_root=project_root)


def test_forbidden_keys_in_project_config(temp_config_dir):
    dacrew_dir, project_root = temp_config_dir
    global_config_path = dacrew_dir / "config.yml"
    project_config_path = project_root / ".dacrew.yml"

    write_yaml(global_config_path, {
        "jira": {"url": "https://example.com", "username": "user", "api_token": "token"},
        "ai": {"openai_api_key": "key"}
    })
    write_yaml(project_config_path, {
        "project": "my-project",
        "ai": {"openai_api_key": "bad-key"}
    })

    with pytest.raises(ValueError, match="ai.openai_api.*must NOT be defined"):
        Config.load(project_root=project_root)