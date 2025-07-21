#!/usr/bin/env python3
"""Setup script for Dacrew project"""

from pathlib import Path

def create_directory_structure():
    """Create the complete directory structure"""
    # Get the project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent

    directories = [
        'src/agents',
        'src/codebase',
        'src/workflows',
        'src/utils',
        'src/web/templates',
        'models/trained',
        'models/checkpoints',
        'data/embeddings',
        'data/models',
        'data/training',
        'data/cache',
        'data/exports',
        'tests/unit',
        'tests/integration',
        'tests/e2e',
        'tests/fixtures',
        'scripts/data_processing',
        'scripts/model_training',
        'scripts/deployment',
        'docs/api',
        'docs/examples',
        'config/environments',
        'config/models',
        'notebooks/exploratory',
        'notebooks/training',
        'notebooks/analysis',
        'logs'
    ]

    print("Creating directory structure...")
    for directory in directories:
        # Create directory relative to project root
        full_path = project_root / directory
        full_path.mkdir(parents=True, exist_ok=True)

        # Create .gitkeep files to ensure directories are tracked
        gitkeep_file = full_path / '.gitkeep'
        if not gitkeep_file.exists():
            gitkeep_file.touch()

    print("✓ Directory structure created successfully")

def create_init_files():
    """Create __init__.py files"""
    # Get the project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent

    init_files = [
        'src/__init__.py',
        'src/agents/__init__.py',
        'src/codebase/__init__.py',
        'src/workflows/__init__.py',
        'src/utils/__init__.py',
        'src/web/__init__.py',
        'models/__init__.py',
        'tests/__init__.py',
        'tests/unit/__init__.py',
        'tests/integration/__init__.py',
        'tests/e2e/__init__.py',
        'tests/fixtures/__init__.py'
    ]

    print("Creating __init__.py files...")
    for init_file in init_files:
        # Create file relative to project root
        init_path = project_root / init_file
        if not init_path.exists():
            init_path.touch()

    print("✓ __init__.py files created successfully")

def main():
    """Main setup function"""
    print("Setting up Dacrew project structure...")
    print(f"Project root: {Path(__file__).parent.parent}")
    create_directory_structure()
    create_init_files()
    print("✓ Project setup complete!")
    print("\nNext steps:")
    print("1. Copy the code snippets from the previous response into their respective files")
    print("2. Run: pip install -r requirements.txt")
    print("3. Copy .env.example to .env and configure your settings")

if __name__ == "__main__":
    main()