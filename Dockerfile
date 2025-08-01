# Multi-stage build for PyAirtable Platform Services
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install pytest pytest-asyncio black isort mypy

# Copy source code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

# Expose port
EXPOSE 8007

# Run development server with auto-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007", "--reload"]

# Production stage
FROM base as production

# Copy source code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

# Expose port
EXPOSE 8007

# Run production server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007", "--workers", "1"]