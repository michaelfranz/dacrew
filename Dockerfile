# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements-minimal.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY dacrew/ ./dacrew/
COPY config.yml .

# Create directories for embeddings and logs
RUN mkdir -p /app/embeddings /app/logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash dacrew && \
    chown -R dacrew:dacrew /app

# Switch to non-root user
USER dacrew

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["uvicorn", "dacrew.server:app", "--host", "0.0.0.0", "--port", "8080"]
