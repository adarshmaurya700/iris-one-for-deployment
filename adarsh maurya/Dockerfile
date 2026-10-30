# Production Container for IRIS onE (FastAPI + Vanilla JS SPA)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_PATH=/data/iris_one.db \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install lightweight dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create persistent storage mount point
RUN mkdir -p /data

# Install Python requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy source code and frontend assets
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Expose HTTP port (Render, Railway, Fly.io, Cloud Run inject $PORT)
EXPOSE 8000

# Health check using the /api/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start Uvicorn production server
CMD ["sh", "-c", "cd /app/backend && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
