"""Custom exceptions for embedding operations"""


class EmbeddingError(Exception):
    """Base exception for embedding operations"""
    pass


class EmbeddingNotFoundError(EmbeddingError):
    """Raised when requested embeddings do not exist"""
    pass


class EmbeddingIndexError(EmbeddingError):
    """Raised when embedding indexing fails"""
    pass