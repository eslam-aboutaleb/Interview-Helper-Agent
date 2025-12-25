FROM python:3.11-slim

# Set environment variables to prevent debconf warnings
ENV DEBIAN_FRONTEND=noninteractive \
    DEBCONF_NOWARNINGS=yes

# System dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    python3-venv \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set up virtual environment
RUN python -m venv /app/venv

# Make sure we use the virtualenv
ENV PATH="/app/venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/venv"

# Install Python deps in the virtual environment and create user in a single layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn uvicorn python-multipart && \
    useradd -m appuser && \
    chown -R appuser:appuser /app

# Copy app code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose internal port
EXPOSE 8000

CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60"]
