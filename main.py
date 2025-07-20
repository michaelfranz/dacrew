"""Main entry point for DaCrew - AI-powered Development Crew"""

import sys
import warnings
from pathlib import Path

# Suppress the specific HuggingFace warning about resume_download
warnings.filterwarnings("ignore", message=".*resume_download.*", category=FutureWarning)

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli import app

if __name__ == "__main__":
    app()