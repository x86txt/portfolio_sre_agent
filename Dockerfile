# Multi-stage Dockerfile for aiTriage (fly.io deployment)
# Stage 1: Build the Astro frontend
FROM oven/bun:canary-slim AS frontend-builder

WORKDIR /build

# Copy frontend package files
COPY frontend/package.json ./frontend/

# Install frontend dependencies
RUN cd frontend && bun install --frozen-lockfile

# Copy frontend source
COPY frontend ./frontend

# Build static Astro site
RUN bun run --cwd frontend build

# Stage 2: Python backend runtime
FROM python:3-slim

WORKDIR /app

# Install uv for faster pip operations
RUN pip install --no-cache-dir uv

# Copy backend requirements
COPY backend/requirements.txt backend/requirements-dev.txt ./

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Copy backend source
COPY backend/app ./app

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/frontend/dist ./static

# Create cache directory for SQLite database
# Note: SQLite3 is built into Python (sqlite3 module) and comes with python:3-slim
RUN mkdir -p /app/cache && chmod 755 /app/cache

# Set default cache directory (can be overridden via env var)
ENV CACHE_DB_DIR=/app/cache

# Expose port (fly.io defaults to 8080, but we'll use 8000 and configure fly.toml)
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

