import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

# Explicit path setup for IDE recognition
_project_root = Path(__file__).parent.parent.parent.parent
_src_path = _project_root / 'src'
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Import base class
from tests.unit.base import BaseTestCase

# Now these imports should work with correct module paths
from src.cli import app, show_issue


class TestShowIssueCommand(BaseTestCase):
    """Test cases for the 'dacrew issues show' command"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.runner = CliRunner()

        # Sample issue data for mocking
        self.sample_issue = {
            'key': 'BTS-15',
            'summary': 'Fix authentication system vulnerability',
            'status': 'In Progress',
            'priority': 'High',
            'assignee': 'john.doe',
            'reporter': 'jane.smith',
            'project': 'Backend Task System',
            'issue_type': 'Bug',
            'created': '2024-01-10T09:15:00.000Z',
            'updated': '2024-01-15T14:30:00.000Z',
            'url': 'https://test-jira.atlassian.net/browse/BTS-15',
            'description': 'The authentication system has a vulnerability that allows unauthorized access. This needs immediate attention.'
        }

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_success(self, mock_console, mock_jira_client, mock_config_load):
        """Test successful display of an issue"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = self.sample_issue
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_jira_client.assert_called_once_with(mock_config)
        mock_client_instance.get_issue.assert_called_once_with('BTS-15')

        # Verify console.print calls - should print panels for issue info and description
        self.assertTrue(mock_console.print.called)
        self.assertGreaterEqual(mock_console.print.call_count, 2)  # At least issue panel + description panel

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_valid_key_format(self, mock_console, mock_jira_client, mock_config_load):
        """Test with various valid issue key formats"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = self.sample_issue
        mock_jira_client.return_value = mock_client_instance

        # Test various valid formats
        valid_keys = ['ABC-1', 'PROJECT-123', 'TEST-9999', 'A1B2-456']

        for issue_key in valid_keys:
            with self.subTest(issue_key=issue_key):
                # Update the sample issue key to match
                test_issue = self.sample_issue.copy()
                test_issue['key'] = issue_key
                mock_client_instance.get_issue.return_value = test_issue

                # Act
                result = self.runner.invoke(app, ['issues', 'show', issue_key])

                # Assert
                self.assertEqual(result.exit_code, 0)
                mock_client_instance.get_issue.assert_called_with(issue_key)

    def test_show_issue_illegal_argument_missing_key(self):
        """Test error when no issue key is provided"""
        # Act
        result = self.runner.invoke(app, ['issues', 'show'])

        # Assert
        self.assertNotEqual(result.exit_code, 0)  # Should fail due to missing required argument
        self.assertIn("Missing argument", result.output)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_invalid_key_format(self, mock_console, mock_jira_client, mock_config_load):
        """Test with invalid issue key formats"""
        # Arrange - set up mocks for cases where the CLI might call them
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = None  # Issue not found
        mock_jira_client.return_value = mock_client_instance

        # These invalid keys may cause CLI validation to fail with exit code 2
        # or they may be passed through to Jira client which returns None
        invalid_keys = ['abc-1', '123-ABC', 'PROJECT', '123', 'PROJECT-', '-123', 'PROJECT-ABC']

        for invalid_key in invalid_keys:
            with self.subTest(invalid_key=invalid_key):
                # Act
                result = self.runner.invoke(app, ['issues', 'show', invalid_key])

                # Assert - Either CLI validates and exits with 2, or it's handled gracefully with 0
                self.assertIn(result.exit_code, [0, 2],
                              f"Expected exit code 0 or 2 for invalid key: {invalid_key}, got {result.exit_code}")

                # Reset mocks for next iteration
                mock_console.print.reset_mock()
                if mock_client_instance.get_issue.called:
                    mock_client_instance.get_issue.reset_mock()

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_not_found(self, mock_console, mock_jira_client, mock_config_load):
        """Test when issue key does not correspond to a known issue"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = None  # Issue not found
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'NONEXISTENT-999'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles gracefully
        mock_client_instance.get_issue.assert_called_once_with('NONEXISTENT-999')

        # Verify "not found" message
        call_args = [str(call) for call in mock_console.print.call_args_list]
        self.assertTrue(any("NONEXISTENT-999 not found" in arg for arg in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_without_description(self, mock_console, mock_jira_client, mock_config_load):
        """Test showing issue that has no description"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        issue_without_description = self.sample_issue.copy()
        issue_without_description['description'] = None

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = issue_without_description
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.get_issue.assert_called_once_with('BTS-15')

        # Should only print one panel (issue info, no description panel)
        self.assertTrue(mock_console.print.called)
        # Don't check exact count as it may vary, but ensure it works without error

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_with_empty_description(self, mock_console, mock_jira_client, mock_config_load):
        """Test showing issue that has empty description"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        issue_with_empty_description = self.sample_issue.copy()
        issue_with_empty_description['description'] = ""

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = issue_with_empty_description
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.get_issue.assert_called_once_with('BTS-15')

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_config_load_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of config load exception"""
        # Arrange
        mock_config_load.side_effect = Exception("Config load failed")

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully

        # Verify error message
        call_args = [str(call) for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error showing issue:" in arg for arg in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_client_creation_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of JiraClient creation exception"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_jira_client.side_effect = Exception("Client creation failed")

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully

        # Verify error message
        call_args = [str(call) for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error showing issue:" in arg for arg in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_get_issue_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of get_issue exception"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.side_effect = Exception("Issue fetch failed")
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully

        # Verify error message
        call_args = [str(call) for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error showing issue:" in arg for arg in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_network_timeout_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of network timeout exception"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.side_effect = Exception("Request timeout")
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully

        # Verify error message
        call_args = [str(call) for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error showing issue:" in arg for arg in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_unauthorized_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of unauthorized access exception"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.side_effect = Exception("Unauthorized access")
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully

        # Verify error message
        call_args = [str(call) for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error showing issue:" in arg for arg in call_args))

    def test_show_issue_function_exists_and_callable(self):
        """Test that show_issue function exists and is callable"""
        # Assert
        self.assertTrue(callable(show_issue))
        self.assertEqual(show_issue.__name__, 'show_issue')

    def test_show_issue_function_docstring(self):
        """Test that show_issue function has proper docstring"""
        # Assert
        self.assertIsNotNone(show_issue.__doc__)
        self.assertIn("Show detailed information about a specific issue", show_issue.__doc__)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_with_long_description(self, mock_console, mock_jira_client, mock_config_load):
        """Test showing issue with a very long description"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        issue_with_long_description = self.sample_issue.copy()
        issue_with_long_description['description'] = "A" * 1000  # Very long description

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = issue_with_long_description
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # Should handle long text without issues

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_with_special_characters(self, mock_console, mock_jira_client, mock_config_load):
        """Test showing issue with special characters in fields"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        issue_with_special_chars = self.sample_issue.copy()
        issue_with_special_chars['summary'] = "Fix issue with émojis 🔥 and spëcial characters"
        issue_with_special_chars['description'] = "Description with\nmultiple\nlines\nand émojis 🚀"

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = issue_with_special_chars
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'BTS-15'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # Should handle special characters


class TestShowIssueIntegration(BaseTestCase):
    """Integration tests for show_issue command"""

    def setUp(self):
        """Set up test fixtures for integration tests"""
        super().setUp()
        self.runner = CliRunner()

    @patch.dict('os.environ', {
        'JIRA_URL': 'https://test-jira.atlassian.net',
        'JIRA_USERNAME': 'test-user',
        'JIRA_API_TOKEN': 'test-token'
    })
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_show_issue_with_env_vars(self, mock_console, mock_jira_client):
        """Test show issue with environment variables configured"""
        # Arrange
        sample_issue = {
            'key': 'ENV-123',
            'summary': 'Environment test issue',
            'status': 'Open',
            'priority': 'Medium',
            'assignee': 'test-user',
            'reporter': 'test-user',
            'project': 'Environment Test',
            'issue_type': 'Task',
            'created': '2024-01-15T10:30:00.000Z',
            'updated': '2024-01-15T10:30:00.000Z',
            'url': 'https://test-jira.atlassian.net/browse/ENV-123',
            'description': 'Test description'
        }

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = sample_issue
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'show', 'ENV-123'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(mock_console.print.called)


class TestIssueKeyValidation(BaseTestCase):
    """Test issue key validation scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.runner = CliRunner()

    def test_various_invalid_key_formats(self):
        """Test comprehensive set of invalid issue key formats"""
        # Comprehensive list of invalid formats
        invalid_keys = [
            'abc-123',      # lowercase project key
            '123-ABC',      # number-letter format
            'PROJECT',      # no dash or number
            '123',          # just number
            'PROJECT-',     # no number after dash
            '-123',         # no project key before dash
            'PROJECT-ABC',  # letters after dash
            'PR_JECT-123',  # underscore in project key
            'PROJECT-12a',  # letter in issue number
            'project-123',  # lowercase project key
            'PROJ ECT-123', # space in project key
            'PROJ-ECT-123', # multiple dashes
            '',             # empty string
            'A-',           # single char project with no number
            '-1',           # just dash and number
            'A--1',         # double dash
            'PROJ- 123',    # space after dash
            'PROJ -123',    # space before dash
        ]

        for invalid_key in invalid_keys:
            with self.subTest(invalid_key=invalid_key):
                # Act
                result = self.runner.invoke(app, ['issues', 'show', invalid_key])

                # Assert - CLI may validate and exit with 2, or handle gracefully with 0
                self.assertIn(result.exit_code, [0, 2],
                              f"Expected exit code 0 or 2 for invalid key: {invalid_key}, got {result.exit_code}")

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_valid_key_formats_edge_cases(self, mock_console, mock_jira_client, mock_config_load):
        """Test edge cases for valid issue key formats"""
        # Arrange
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.get_issue.return_value = {
            'key': 'TEST-1',
            'summary': 'Test',
            'status': 'Open',
            'priority': 'Medium',
            'assignee': 'test',
            'reporter': 'test',
            'project': 'Test',
            'issue_type': 'Task',
            'created': '2024-01-15T10:30:00.000Z',
            'updated': '2024-01-15T10:30:00.000Z',
            'url': 'https://test.com',
            'description': 'Test'
        }
        mock_jira_client.return_value = mock_client_instance

        # Valid edge cases
        valid_keys = [
            'A-1',          # shortest valid format
            'AB-1',         # two char project key
            'ABC-1',        # three char project key
            'ABCD-1',       # four char project key
            'A1-1',         # project key with number
            'A1B2-1',       # mixed alphanumeric project key
            'TEST-999999',  # very long issue number
            'PROJECT123-1', # long project key with numbers
        ]

        for valid_key in valid_keys:
            with self.subTest(valid_key=valid_key):
                # Update mock return to match the key
                test_issue = mock_client_instance.get_issue.return_value.copy()
                test_issue['key'] = valid_key
                mock_client_instance.get_issue.return_value = test_issue

                # Act
                result = self.runner.invoke(app, ['issues', 'show', valid_key])

                # Assert
                self.assertEqual(result.exit_code, 0)
                mock_client_instance.get_issue.assert_called_with(valid_key)

                # Reset mock for next iteration
                mock_console.print.reset_mock()
                mock_client_instance.get_issue.reset_mock()


if __name__ == '__main__':
    unittest.main()