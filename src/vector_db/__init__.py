"""Vector Database Management Package"""

from .vector_manager import VectorManager
from .exceptions import VectorDBError, CollectionNotFoundError, EmbeddingError

__all__ = [
    # Main manager
    'VectorManager',

    # Exceptions
    'VectorDBError',
    'CollectionNotFoundError',
    'EmbeddingError',
]

__version__ = "1.0.0"