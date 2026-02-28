FROM python:3.12-slim

WORKDIR /app

# Install git for pip git dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY agents/ agents/
COPY scripts/ scripts/

# Default: run all agents
ENTRYPOINT ["python", "scripts/run.py"]
CMD ["all"]
