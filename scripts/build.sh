#!/bin/bash

# Build script for dacrew
set -e

echo "🚀 Building dacrew..."

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Please run this script from the project root."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run tests
echo "🧪 Running tests..."
python -m pytest tests/ -v

# Run linting
echo "🔍 Running linting..."
python -m black dacrew/ tests/ --check
python -m isort dacrew/ tests/ --check-only
python -m mypy dacrew/

echo "✅ Build completed successfully!"
