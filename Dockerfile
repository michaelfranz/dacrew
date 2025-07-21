FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies with conflict resolution
RUN python -m pip install --upgrade pip && \
    # Install pytest tools first (lightweight)
    pip install pytest pytest-cov pytest-timeout pytest-xdist pytest-html && \
    # Handle dependency conflicts by installing in order
    pip install --upgrade tokenizers>=0.20.3 && \
    pip install --upgrade transformers>=4.45.0 && \
    pip install --upgrade crewai && \
    # Now install other requirements, skipping conflicting ones
    grep -v "^crewai" requirements.txt | grep -v "^transformers" | grep -v "^tokenizers" | \
    xargs -I {} sh -c 'pip install "{}" || echo "Skipped conflicting package: {}"' && \
    # Verify key packages are working
    python -c "import crewai; print(f'CrewAI: {crewai.__version__}')" && \
    python -c "import transformers; print(f'Transformers: {transformers.__version__}')" && \
    python -c "import pytest; print('Pytest: OK')"

# Set default command
CMD ["pytest"]