# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for App Migrator with Frappe V16
# Stage 1: Builder
FROM python:3.14-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    libpq-dev \
    curl \
    git \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set up workspace
WORKDIR /workspace

# Install flit for pyproject.toml based builds
RUN pip install --no-cache-dir flit_core>=3.4

# Clone Frappe framework
ARG FRAPPE_VERSION=16
RUN git clone --depth 1 --branch version-${FRAPPE_VERSION} https://github.com/frappe/frappe.git

# Stage 2: Production
FROM python:3.14-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    mariadb-client \
    redis-server \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create frappe user
RUN groupadd --gid 1000 frappe && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home frappe

# Set up workspace
WORKDIR /home/frappe/frappe-bench

# Copy Frappe from builder
COPY --from=builder /workspace/frappe /home/frappe/frappe-bench/apps/frappe

# Install frappe dependencies
RUN pip install --no-cache-dir --break-system-packages \
    frappe==${FRAPPE_VERSION} \
    redis \
    mariadb-connector-python \
    Pillow \
    PyYAML \
    python-dateutil \
    requests

# Install app_migrator
COPY --chown=frappe:frappe pyproject.toml README.md /home/frappe/frappe-bench/apps/app_migrator/
COPY --chown=frappe:frappe app_migrator/ /home/frappe/frappe-bench/apps/app_migrator/app_migrator/

# Create sites directory
RUN mkdir -p /home/frappe/frappe-bench/sites/assets && \
    chown -R frappe:frappe /home/frappe

# Switch to non-root user
USER frappe

# Environment variables
ENV FRAPPE_DATA_DIR=/home/frappe/frappe-bench/sites
ENV PYTHONUNBUFFERED=1
ENV FRAPPE_ALLOW_BROKEN_PIP=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/method/health || exit 1

# Expose ports
EXPOSE 8000 9000

# Default command
CMD ["python", "-m", "frappe", "app"]