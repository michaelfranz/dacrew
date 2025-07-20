"""Vector Database Exception Classes"""


class VectorDBError(Exception):
    """Base exception for vector database operations"""
    pass


class CollectionNotFoundError(VectorDBError):
    """Raised when a requested collection does not exist"""
    pass


class EmbeddingError(VectorDBError):
    """Raised when embedding operations fail"""
    pass


class ConnectionError(VectorDBError):
    """Raised when connection to vector database fails"""
    pass


class InvalidQueryError(VectorDBError):
    """Raised when query parameters are invalid"""
    pass