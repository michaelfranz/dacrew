"""Setup script for DaCrew - AI-powered Development Crew"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dacrew",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered development crew - your team of software development assistants",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "crewai>=0.28.8",
        "jira>=3.5.2",
        "chromadb>=0.4.24",
        "sentence-transformers>=2.7.0",
        "typer>=0.12.3",
        "rich>=13.7.1",
        "python-dotenv>=1.0.1",
        "langchain>=0.1.16",
        "openai>=1.21.1",
    ],
    entry_points={
        "console_scripts": [
            "dacrew=src.cli:app",
        ],
    },
)