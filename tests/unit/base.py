import sys
import tempfile
import unittest
from pathlib import Path

# Add src directory to Python path - do this at module level
# This needs to be done before any imports from src/
_project_root = Path(__file__).parent.parent.parent
_src_path = _project_root / 'src'

# Ensure src path is in sys.path for imports
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Also add project root for relative imports
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

class BaseTestCase(unittest.TestCase):
    """Abstract base class for all dacrew unit tests"""

    def setUp(self):
        """Common setup for all tests"""
        # Setup temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(self.cleanup_temp_dir)

        # Mock common external dependencies
        self.mock_config = self.setup_mock_config()
        self.mock_logger = self.setup_mock_logger()

    def cleanup_temp_dir(self):
        """Clean up temporary directory"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def setup_mock_config(self):
        """Setup mock configuration"""
        from unittest.mock import Mock
        mock_config = Mock()
        # Add common config attributes
        mock_config.jira.url = "https://test-jira.atlassian.net"
        mock_config.jira.username = "test-user"
        mock_config.jira.api_token = "test-token"
        return mock_config

    def setup_mock_logger(self):
        """Setup mock logger"""
        from unittest.mock import Mock
        return Mock()