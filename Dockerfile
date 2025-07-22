FROM python:3.10-slim

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy test requirements (not the full requirements.txt)
COPY requirements-test.txt .

# Install test dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-test.txt

# Copy source code
COPY . .

CMD ["pytest", "tests/unit/", "-v"]