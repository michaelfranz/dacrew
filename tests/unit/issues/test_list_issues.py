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
from src.cli import app, list_issues


class TestListIssuesCommand(BaseTestCase):
    """Test cases for the 'dacrew issues list' command"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.runner = CliRunner()
        
        # Sample issue data for mocking
        self.sample_issues = [
            {
                'key': 'TEST-123',
                'summary': 'Fix login bug in authentication system',
                'status': 'In Progress',
                'assignee': 'john.doe',
                'updated': '2024-01-15T10:30:00.000Z'
            },
            {
                'key': 'TEST-124', 
                'summary': 'Add new feature for user dashboard with enhanced analytics and reporting capabilities',
                'status': 'To Do',
                'assignee': 'jane.smith',
                'updated': '2024-01-14T15:45:00.000Z'
            },
            {
                'key': 'TEST-125',
                'summary': 'Update documentation',
                'status': 'Done',
                'assignee': 'bob.wilson',
                'updated': '2024-01-13T09:20:00.000Z'
            }
        ]

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_success_no_filters(self, mock_console, mock_jira_client, mock_config_load):
        """Test successful listing of issues without filters"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"  # <-- Updated for new config structure
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['issues', 'list'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_jira_client.assert_called_once_with(mock_config)
        mock_client_instance.search_issues.assert_called_once_with("project = TEST", max_results=10)

        call_args = [call[0] for call in mock_console.print.call_args_list]
        self.assertTrue(any("🔍 Searching with JQL:" in str(args) for args in call_args))


    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_with_project_filter(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues with project filter"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "DEFAULT"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list', '--project', 'MYPROJ'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.search_issues.assert_called_once_with("project = MYPROJ", max_results=10)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_with_status_filter(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues with status filter"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues[:1]  # Only one issue
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list', '--status', 'In Progress'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.search_issues.assert_called_once_with("project = TEST AND status = 'In Progress'", max_results=10)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_with_assignee_filter(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues with assignee filter"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues[:1]  # Only one issue
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list', '--assignee', 'john.doe'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.search_issues.assert_called_once_with("project = TEST AND assignee = 'john.doe'", max_results=10)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_with_multiple_filters(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues with multiple filters"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "DEFAULT"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues[:1]  # Only one issue
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list', 
                                        '--project', 'MYPROJ',
                                        '--status', 'Done',
                                        '--assignee', 'bob.wilson'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        expected_jql = "project = MYPROJ AND status = 'Done' AND assignee = 'bob.wilson'"
        mock_client_instance.search_issues.assert_called_once_with(expected_jql, max_results=10)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_with_custom_limit(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues with custom limit"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues[:5]
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list', '--limit', '5'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.search_issues.assert_called_once_with("project = TEST", max_results=5)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_no_default_project(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues when no default project is configured"""
        # Arrange
        mock_config = Mock()
        mock_config.project = ""
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.search_issues.assert_called_once_with("order by updated DESC", max_results=10)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_no_results_found(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues when no results are found"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = []  # Empty results
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        mock_client_instance.search_issues.assert_called_once_with("project = TEST", max_results=10)
        
        # Verify "No issues found" message
        call_args = [call[0] for call in mock_console.print.call_args_list]
        self.assertTrue(any("No issues found" in str(args) for args in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_long_summary_truncation(self, mock_console, mock_jira_client, mock_config_load):
        """Test that long summaries are properly truncated in the table"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues  # Contains long summary
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        # The test passes if no exception is thrown - truncation logic should handle long summaries

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_config_load_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of config load exception"""
        # Arrange
        mock_config_load.side_effect = Exception("Config load failed")
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully
        
        # Verify error message
        call_args = [call[0] for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error listing issues:" in str(args) for args in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_client_creation_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of JiraClient creation exception"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"
        mock_config_load.return_value = mock_config
        
        mock_jira_client.side_effect = Exception("Client creation failed")
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully
        
        # Verify error message
        call_args = [call[0] for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error listing issues:" in str(args) for args in call_args))

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_search_exception(self, mock_console, mock_jira_client, mock_config_load):
        """Test handling of search_issues exception"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "TEST"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.side_effect = Exception("Search failed")
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI handles exception gracefully
        
        # Verify error message
        call_args = [call[0] for call in mock_console.print.call_args_list]
        self.assertTrue(any("❌ Error listing issues:" in str(args) for args in call_args))

    def test_list_issues_function_exists_and_callable(self):
        """Test that list_issues function exists and is callable"""
        # Assert
        self.assertTrue(callable(list_issues))
        self.assertEqual(list_issues.__name__, 'list_issues')

    def test_list_issues_function_docstring(self):
        """Test that list_issues function has proper docstring"""
        # Assert
        self.assertIsNotNone(list_issues.__doc__)
        self.assertIn("List Jira issues", list_issues.__doc__)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_short_options(self, mock_console, mock_jira_client, mock_config_load):
        """Test listing issues using short option flags"""
        # Arrange
        mock_config = Mock()
        mock_config.project = "DEFAULT"
        mock_config_load.return_value = mock_config
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = self.sample_issues[:1]
        mock_jira_client.return_value = mock_client_instance
        
        # Act - using short options
        result = self.runner.invoke(app, ['issues', 'list', '-p', 'PROJ', '-s', 'Done', '-a', 'user', '-l', '5'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        expected_jql = "project = PROJ AND status = 'Done' AND assignee = 'user'"
        mock_client_instance.search_issues.assert_called_once_with(expected_jql, max_results=5)


class TestListIssuesIntegration(BaseTestCase):
    """Integration tests for list_issues command"""
    
    def setUp(self):
        """Set up test fixtures for integration tests"""
        super().setUp()
        self.runner = CliRunner()
    
    @patch.dict('os.environ', {
        'JIRA_URL': 'https://test-jira.atlassian.net',
        'JIRA_USERNAME': 'test-user',
        'JIRA_API_TOKEN': 'test-token',
        'DEFAULT_PROJECT_KEY': 'TESTPROJ'
    })
    @patch('src.jira_client.JiraClient')
    @patch('src.cli.console')
    def test_list_issues_with_env_vars(self, mock_console, mock_jira_client):
        """Test list issues with environment variables configured"""
        # Arrange
        sample_issues = [
            {
                'key': 'TESTPROJ-1',
                'summary': 'Test issue',
                'status': 'Open',
                'assignee': 'test-user',
                'updated': '2024-01-15T10:30:00.000Z'
            }
        ]
        
        mock_client_instance = Mock()
        mock_client_instance.search_issues.return_value = sample_issues
        mock_jira_client.return_value = mock_client_instance
        
        # Act
        result = self.runner.invoke(app, ['issues', 'list'])
        
        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(mock_console.print.called)


if __name__ == '__main__':
    unittest.main()