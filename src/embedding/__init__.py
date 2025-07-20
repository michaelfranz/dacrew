"""Embedding Management Module - Repository-Embedding Coordination"""

from .embedding_manager import EmbeddingManager, EmbeddingMetadata
from .exceptions import EmbeddingError, EmbeddingNotFoundError, EmbeddingIndexError

__all__ = [
    # Main coordination manager
    'EmbeddingManager',

    # Utility classes
    'EmbeddingMetadata',

    # Exceptions
    'EmbeddingError',
    'EmbeddingNotFoundError',
    'EmbeddingIndexError',
]

__version__ = "2.0.0"