"""
Connection-related unit tests for the DaCrew CLI application.

This module contains tests for:
- test-connection command functionality
- Jira connectivity validation
- Authentication testing
- Error handling for connection failures

Test classes:
- TestConnectionCommand: Tests for the dacrew test-connection command
- TestJiraConnection: Tests for underlying Jira client connection logic
"""

# Import test classes for easy discovery by test runners
from .test_connection import TestConnectionCommand

__all__ = [
    'TestConnectionCommand',
]

# Connection test specific constants
CONNECTION_TEST_CONFIG = {
    'TIMEOUT_SECONDS': 10,
    'RETRY_ATTEMPTS': 3,
    'EXPECTED_SUCCESS_MESSAGE': 'Connection test successful',
    'EXPECTED_FAILURE_MESSAGE': 'Connection test failed',
}

# Mock response templates for connection tests
MOCK_CONNECTION_RESPONSES = {
    'success_response': {
        'displayName': 'Test User',
        'emailAddress': 'test@example.com',
        'accountId': 'test-account-id-123'
    },
    'auth_error_response': {
        'error': 'Unauthorized',
        'status_code': 401,
        'message': 'Authentication failed'
    },
    'network_error_response': {
        'error': 'ConnectionError',
        'message': 'Failed to connect to Jira instance'
    }
}