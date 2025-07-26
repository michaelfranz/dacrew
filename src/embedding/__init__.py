"""Embedding Management Module - Repository-Embedding Coordination"""

from .embedding_manager import EmbeddingManager
from .exceptions import EmbeddingError, EmbeddingNotFoundError, EmbeddingIndexError

__all__ = [
    # Main coordination manager
    'EmbeddingManager',

    # Exceptions
    'EmbeddingError',
    'EmbeddingNotFoundError',
    'EmbeddingIndexError',
]

__version__ = "2.0.0"