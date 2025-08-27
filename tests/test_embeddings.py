import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from dacrew.config import AppConfig, CodebaseConfig, DocumentsConfig, EmbeddingConfig
from dacrew.embeddings import EmbeddingManager


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    config = AppConfig(
        jira=Mock(url="https://test.atlassian.net", user_id="test@example.com", token="test-token"),
        embedding=EmbeddingConfig(
            model="sentence-transformers/all-MiniLM-L6-v2",
            chunk_size=512,
            chunk_overlap=50,
            workspace_path="./test_embeddings",
            max_workers=2
        ),
        projects=[
            Mock(
                project_id="TEST",
                codebase=CodebaseConfig(
                    repo="https://github.com/test/repo",
                    include_patterns=["**/*.py"],
                    exclude_patterns=["node_modules/**"],
                    update_frequency_hours=24
                ),
                documents=DocumentsConfig(
                    paths=["test_docs/README.md"],
                    urls=["https://example.com/docs"],
                    update_frequency_hours=168
                )
            )
        ]
    )
    return config


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_embedding_manager_initialization(sample_config):
    """Test that EmbeddingManager can be initialized."""
    manager = EmbeddingManager(sample_config)
    assert manager.config == sample_config
    assert manager.workspace_path.exists()


def test_project_workspace_path(sample_config):
    """Test project workspace path generation."""
    manager = EmbeddingManager(sample_config)
    workspace = manager.get_project_workspace("TEST")
    assert workspace.name == "TEST"
    assert workspace.parent == manager.workspace_path


def test_embedding_file_paths(sample_config):
    """Test embedding file path generation."""
    manager = EmbeddingManager(sample_config)
    
    codebase_file = manager.get_embedding_file("TEST", "codebase")
    documents_file = manager.get_embedding_file("TEST", "documents")
    
    assert codebase_file.name == "codebase_embeddings.npz"
    assert documents_file.name == "documents_embeddings.npz"


def test_metadata_file_paths(sample_config):
    """Test metadata file path generation."""
    manager = EmbeddingManager(sample_config)
    
    codebase_meta = manager.get_metadata_file("TEST", "codebase")
    documents_meta = manager.get_metadata_file("TEST", "documents")
    
    assert codebase_meta.name == "codebase_metadata.json"
    assert documents_meta.name == "documents_metadata.json"


def test_should_update_embeddings_new_project(sample_config):
    """Test that embeddings should be updated for new projects."""
    manager = EmbeddingManager(sample_config)
    
    # Should update if metadata file doesn't exist
    assert manager.should_update_embeddings("NEW_PROJECT", "codebase", 24)


def test_text_splitting():
    """Test text splitting functionality."""
    config = AppConfig(
        jira=Mock(url="https://test.atlassian.net", user_id="test@example.com", token="test-token"),
        embedding=EmbeddingConfig(chunk_size=10, chunk_overlap=2)
    )
    manager = EmbeddingManager(config)
    
    text = "This is a test document with multiple words"
    chunks = manager._split_text(text, 10, 2)
    
    assert len(chunks) > 1
    assert all(len(chunk) <= 10 for chunk in chunks)


@patch('dacrew.embeddings.SentenceTransformer')
def test_embedding_manager_with_mock_model(mock_transformer, sample_config):
    """Test embedding manager with mocked transformer."""
    # Mock the transformer
    mock_model = Mock()
    mock_model.encode.return_value = [[0.1, 0.2, 0.3]]  # Mock embeddings
    mock_transformer.return_value = mock_model
    
    manager = EmbeddingManager(sample_config)
    
    # Test that the model was initialized with correct parameters
    mock_transformer.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")


def test_config_loading_with_embeddings():
    """Test that configuration can be loaded with embedding settings."""
    config_data = {
        "jira": {
            "url": "https://test.atlassian.net",
            "user_id": "test@example.com",
            "token": "test-token"
        },
        "embedding": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "chunk_size": 512,
            "chunk_overlap": 50,
            "workspace_path": "./embeddings"
        },
        "projects": [
            {
                "project_id": "TEST",
                "type_status_map": {
                    "Bug": {
                        "To Do": "todo-evaluator"
                    }
                },
                "codebase": {
                    "repo": "https://github.com/test/repo",
                    "include_patterns": ["**/*.py"],
                    "exclude_patterns": ["node_modules/**"]
                },
                "documents": {
                    "paths": ["docs/README.md"],
                    "urls": ["https://example.com/docs"]
                }
            }
        ]
    }
    
    # Mock YAML loading
    with patch('dacrew.config._load_file', return_value=config_data):
        config = AppConfig.load("dummy_path")
        
        assert config.embedding.model == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.embedding.chunk_size == 512
        assert len(config.projects) == 1
        assert config.projects[0].project_id == "TEST"
        assert config.projects[0].codebase is not None
        assert config.projects[0].documents is not None
