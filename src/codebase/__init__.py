"""Codebase Management Module - Pure Repository Operations"""

from .codebase_manager import SimpleCodebaseManager, CrossPlatformLinkManager
from .exceptions import WorkspaceError, GitCloneError

__all__ = [
    # Core managers
    'SimpleCodebaseManager',

    # Utility classes
    'CrossPlatformLinkManager',

    # Exceptions
    'WorkspaceError',
    'GitCloneError',
]

__version__ = "1.0.0"