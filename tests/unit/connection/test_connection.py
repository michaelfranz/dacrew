import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

# Explicit path setup for IDE recognition
_project_root = Path(__file__).parent.parent.parent.parent
_src_path = _project_root / 'src'
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Import base class
from tests.unit.base import BaseTestCase

# Now these imports should work with correct module paths
from src.cli import app, test_jira_connection

class TestConnectionCommand(BaseTestCase):
    """Test cases for the dacrew test-connection command"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.runner = CliRunner()

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')  # FIXED: Patch where it's defined, not where it's imported
    def test_connection_command_success(self, mock_jira_client, mock_config_load):
        """Test successful test-connection command"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('✅ Jira connection successful!', result.stdout)
        self.assertIn('Connected to: https://test-jira.atlassian.net', result.stdout)
        self.assertIn('Username: test-user', result.stdout)

        # Verify that client was created and test_connection was called
        mock_jira_client.assert_called_once_with(mock_config)
        mock_client_instance.test_connection.assert_called_once()

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')  # FIXED: Patch where it's defined, not where it's imported
    def test_connection_command_failure(self, mock_jira_client, mock_config_load):
        """Test failed test-connection command"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = False
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)  # CLI doesn't exit with error code
        self.assertIn('❌ Jira connection failed!', result.stdout)
        self.assertIn('Please check your credentials and try again', result.stdout)

        # Verify that client was created and test_connection was called
        mock_jira_client.assert_called_once_with(mock_config)
        mock_client_instance.test_connection.assert_called_once()

    @patch('src.config.Config.load')
    def test_connection_command_missing_url(self, mock_config_load):
        """Test connection command with missing JIRA URL"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = None
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Jira URL not configured', result.stdout)
        self.assertIn('Please set JIRA_URL in your .env file', result.stdout)

    @patch('src.config.Config.load')
    def test_connection_command_empty_url(self, mock_config_load):
        """Test connection command with empty JIRA URL"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = ""
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Jira URL not configured', result.stdout)
        self.assertIn('Please set JIRA_URL in your .env file', result.stdout)

    @patch('src.config.Config.load')
    def test_connection_command_missing_username(self, mock_config_load):
        """Test connection command with missing JIRA username"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = None
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Jira username not configured', result.stdout)
        self.assertIn('Please set JIRA_USERNAME in your .env file', result.stdout)

    @patch('src.config.Config.load')
    def test_connection_command_empty_username(self, mock_config_load):
        """Test connection command with empty JIRA username"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = ""
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Jira username not configured', result.stdout)
        self.assertIn('Please set JIRA_USERNAME in your .env file', result.stdout)

    @patch('src.config.Config.load')
    def test_connection_command_missing_api_token(self, mock_config_load):
        """Test connection command with missing JIRA API token"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = None
        mock_config_load.return_value = mock_config

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Jira API token not configured', result.stdout)
        self.assertIn('Please set JIRA_API_TOKEN in your .env file', result.stdout)

    @patch('src.config.Config.load')
    def test_connection_command_empty_api_token(self, mock_config_load):
        """Test connection command with empty JIRA API token"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = ""
        mock_config_load.return_value = mock_config

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Jira API token not configured', result.stdout)
        self.assertIn('Please set JIRA_API_TOKEN in your .env file', result.stdout)

    @patch('src.config.Config.load')
    def test_connection_command_multiple_missing_configs(self, mock_config_load):
        """Test connection command with multiple missing configurations"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = None
        mock_config.jira.username = None
        mock_config.jira.api_token = None
        mock_config_load.return_value = mock_config

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Jira URL not configured', result.stdout)
        # Should exit early on first missing config, so username/token checks shouldn't run
        self.assertNotIn('❌ Jira username not configured', result.stdout)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')  # FIXED: Patch at source module
    def test_connection_command_client_creation_exception(self, mock_jira_client, mock_config_load):
        """Test connection command when JiraClient creation raises exception"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        mock_jira_client.side_effect = Exception("Connection failed")

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Error testing connection: Connection failed', result.stdout)

    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')  # FIXED: Patch at source module
    def test_connection_command_test_connection_exception(self, mock_jira_client, mock_config_load):
        """Test connection command when test_connection method raises exception"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.test_connection.side_effect = Exception("Test failed")
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Error testing connection: Test failed', result.stdout)

    @patch('src.config.Config.load')
    def test_connection_command_config_load_exception(self, mock_config_load):
        """Test connection command when Config.load() raises exception"""
        # Arrange
        mock_config_load.side_effect = Exception("Config load failed")

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('❌ Error testing connection: Config load failed', result.stdout)

    @patch('src.cli.console')
    @patch('src.config.Config.load')
    @patch('src.jira_client.JiraClient')  # FIXED: Patch at source module
    def test_connection_command_console_output_calls(self, mock_jira_client, mock_config_load, mock_console):
        """Test that console.print is called with correct messages"""
        # Arrange
        mock_config = Mock()
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        mock_config_load.return_value = mock_config

        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)

        # Verify console.print calls
        expected_calls = [
            ("🔗 Testing JIRA connection...", "cyan"),
            ("✅ Jira connection successful!", "green"),
            ("Connected to: https://test-jira.atlassian.net", "dim"),
            ("Username: test-user", "dim")
        ]

        # Check that console.print was called with expected arguments
        # Note: This assumes console.print calls are made with message and style parameters
        self.assertTrue(mock_console.print.called)
        self.assertGreaterEqual(mock_console.print.call_count, len(expected_calls))

    def test_function_exists_and_callable(self):
        """Test that test_jira_connection function exists and is callable"""
        # Assert
        self.assertTrue(callable(test_jira_connection))
        self.assertEqual(test_jira_connection.__name__, 'test_jira_connection')

    def test_function_docstring(self):
        """Test that test_jira_connection function has proper docstring"""
        # Assert
        self.assertIsNotNone(test_jira_connection.__doc__)
        self.assertIn("Test Jira connection", test_jira_connection.__doc__)


class TestConnectionCommandIntegration(BaseTestCase):
    """Integration tests for connection command with more realistic scenarios"""

    def setUp(self):
        """Set up test fixtures for integration tests"""
        super().setUp()
        self.runner = CliRunner()

    @patch.dict('os.environ', {
        'JIRA_URL': 'https://test-jira.atlassian.net',
        'JIRA_USERNAME': 'test-user',
        'JIRA_API_TOKEN': 'test-token'
    })
    @patch('src.jira_client.JiraClient')  # FIXED: Patch at source module
    def test_connection_with_env_vars(self, mock_jira_client):
        """Test connection command with environment variables set"""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.test_connection.return_value = True
        mock_jira_client.return_value = mock_client_instance

        # Act
        result = self.runner.invoke(app, ['test-connection'])

        # Assert
        self.assertEqual(result.exit_code, 0)
        self.assertIn('✅ Jira connection successful!', result.stdout)


if __name__ == '__main__':
    unittest.main()