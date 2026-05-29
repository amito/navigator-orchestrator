# Multi-stage Containerfile for Navigator Orchestrator
# Optimized for Podman with Red Hat UBI base images
#
# Build with: podman build -f Containerfile -t navigator-orchestrator .

# =============================================================================
# Stage 1: Builder - Install dependencies with uv
# =============================================================================
ARG BUILD_PLATFORM=linux/amd64
FROM --platform=${BUILD_PLATFORM} registry.access.redhat.com/ubi9/python-312 AS builder

# Copy uv from official image for fast, reproducible builds
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory (UBI default is /opt/app-root/src)
WORKDIR /opt/app-root/src

# Copy project files for dependency resolution
COPY pyproject.toml uv.lock README.md ./

# Copy source code
COPY src/ ./src/

# Install dependencies and package
RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM --platform=${BUILD_PLATFORM} registry.access.redhat.com/ubi9/python-312 AS runtime

# Labels for container metadata
LABEL org.opencontainers.image.title="Navigator Orchestrator"
LABEL org.opencontainers.image.description="MCP server orchestrating multi-tool workflows against rhoai-mcp"
LABEL org.opencontainers.image.vendor="Red Hat"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /opt/app-root/src

# Copy virtual environment from builder
COPY --from=builder /opt/app-root/src/.venv /opt/app-root/src/.venv

# Copy source code
COPY --from=builder /opt/app-root/src/src /opt/app-root/src/src

# Add virtual environment to PATH
ENV PATH="/opt/app-root/src/.venv/bin:$PATH"

# Environment variables with container-friendly defaults
ENV ORCHESTRATOR_RHOAI_MCP_URL="http://rhoai-mcp:8000/mcp"
ENV ORCHESTRATOR_HOST="0.0.0.0"
ENV ORCHESTRATOR_PORT="8001"

# Expose port for Streamable HTTP transport
EXPOSE 8001

# UBI runs as non-root by default (UID 1001)
USER 1001

# Default entrypoint runs the orchestrator
ENTRYPOINT ["python", "-m", "navigator_orchestrator"]
