# Use a pre-built ML image (smaller than building from scratch)
FROM python:3.10-slim

# Install only essential system packages
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Use pip cache mount and no-cache to reduce image size
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

WORKDIR /app
COPY . .

CMD ["pytest", "tests/unit/", "-v"]