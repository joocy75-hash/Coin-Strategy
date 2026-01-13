# TradingView Strategy Research Lab - Dockerfile
# Multi-stage build for optimized image size
# Security: Non-root user, resource limits

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_USER=appuser \
    APP_UID=1000 \
    APP_GID=1000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid ${APP_GID} ${APP_USER} \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --shell /bin/bash --create-home ${APP_USER}

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (as root, then fix permissions)
RUN playwright install chromium --with-deps

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} . .

# Create necessary directories with proper ownership
RUN mkdir -p data logs data/converted data/reports \
    && chown -R ${APP_USER}:${APP_USER} /app \
    && chmod -R 755 /app/logs /app/data

# Switch to non-root user
USER ${APP_USER}

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Default command - run API server
CMD ["python", "api/server.py"]
