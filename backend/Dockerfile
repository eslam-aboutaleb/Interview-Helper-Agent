FROM python:3.11-slim

# Set environment variables to prevent debconf warnings
ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NOWARNINGS=yes

# System dependencies (curl for healthcheck + uv install)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into the system Python (no venv needed in Docker)
# --frozen ensures the lock file is respected exactly
RUN uv sync --frozen --no-dev --no-install-project

# Copy app code
COPY . .

# Create non-root user and fix ownership
RUN useradd -m appuser && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose internal port
EXPOSE 8000

CMD ["uv", "run", "gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60"]
