"""
Unit tests package for the DaCrew CLI application.

This package contains all unit tests organized by functionality:
- base.py: Abstract base test class with common setup/teardown
- connection/: Connection-related command tests
- test_cli.py: Main CLI interface tests

All test classes should inherit from BaseTestCase in base.py for consistency.
"""

# Import commonly used test utilities for easy access
from .base import BaseTestCase

__all__ = [
    'BaseTestCase',
]

# Test configuration constants
TEST_CONFIG = {
    'DEFAULT_TIMEOUT': 30,
    'MOCK_JIRA_URL': 'https://test-instance.atlassian.net',
    'MOCK_USER_EMAIL': 'test@example.com',
    'TEST_PROJECT_KEY': 'TEST',
}

# Common test fixtures paths
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / 'fixtures'
SAMPLE_CONFIGS_DIR = FIXTURES_DIR / 'sample_configs'
MOCK_RESPONSES_DIR = FIXTURES_DIR / 'mock_responses'

# Ensure fixture directories exist
for directory in [FIXTURES_DIR, SAMPLE_CONFIGS_DIR, MOCK_RESPONSES_DIR]:
    directory.mkdir(exist_ok=True)