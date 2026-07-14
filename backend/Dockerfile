"""
Multi-stage Dockerfile for the ParaRig Ops FastAPI backend.

Build stage: installs dependencies with uv+pip.
Run stage: copies built artifacts, runs Alembic migrations on startup,
           then starts Uvicorn.
"""

# ═══════════════════════════ BUILD STAGE ═══════════════════════════════════
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

# Copy only dependency files for layer caching
COPY pyproject.toml ./

# Install the project dependencies from pyproject.toml
RUN uv pip install --system --no-cache -e .

# Copy application code
COPY app/ app/
COPY alembic.ini ./
COPY pyproject.toml ./

# ═══════════════════════════ RUN STAGE ════════════════════════════════════
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=prod \
    PYTHONPATH=/app

# Install runtime deps for psycopg / health checks (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages + app from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build/app /app
COPY --from=builder /build/alembic.ini /app/alembic.ini
COPY --from=builder /build/pyproject.toml /app/pyproject.toml

WORKDIR /app

EXPOSE 8000

# Startup script: run migrations, then start the server
COPY <<-"STARTUP" /startup.sh
#!/bin/sh
set -e
echo "Running Alembic migrations..."
alembic upgrade head
echo "Starting ParaRig Ops server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
STARTUP

RUN chmod +x /startup.sh

CMD ["/startup.sh"]
