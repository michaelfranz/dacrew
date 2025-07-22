# Use official Python slim image as base (pre-built, optimized)
FROM python:3.10-slim-bullseye

# Set environment variables for better Python behavior in containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy test requirements first (for better Docker layer caching)
COPY requirements-test.txt .

# Install Python dependencies in one layer
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-test.txt

# Copy source code
COPY . .

# Set Python path to find src modules
ENV PYTHONPATH=/app/src:/app

# Default command - run pytest with proper parallel support
CMD ["pytest", "tests/unit/", "-v", "--tb=short"]