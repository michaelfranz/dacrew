# Dockerfile for dacrew
FROM python:3.11-slim

# Ensure stdout/stderr from Python is unbuffered
ENV PYTHONUNBUFFERED=1

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Provide a default location for configuration. Users can mount their own
# configuration file at /config/config.yml and override this path via the
# DACREW_CONFIG environment variable.
RUN mkdir -p /config
ENV DACREW_CONFIG=/config/config.yml

# Expose the application port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "dacrew.server:app", "--host", "0.0.0.0", "--port", "8000"]
