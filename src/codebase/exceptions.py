"""Codebase Management Exception Classes"""


class WorkspaceError(Exception):
    """Base exception for workspace operations"""
    pass


class GitCloneError(WorkspaceError):
    """Raised when git clone operations fail"""
    pass


class RepositoryNotFoundError(WorkspaceError):
    """Raised when a requested repository is not found"""
    pass


class InvalidRepositoryError(WorkspaceError):
    """Raised when repository URL or structure is invalid"""
    pass


class SymlinkError(WorkspaceError):
    """Raised when symlink operations fail"""
    pass