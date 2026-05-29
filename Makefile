# Makefile for Navigator Orchestrator
# Podman-first container management and uv development

# =============================================================================
# Configuration
# =============================================================================

IMAGE_NAME ?= navigator-orchestrator
IMAGE_TAG ?= latest
FULL_IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)
CONTAINER_NAME ?= navigator-orchestrator

# Container runtime detection (prefer podman if available)
CONTAINER_RUNTIME := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

# Runtime configuration
PORT ?= 8001
RHOAI_MCP_URL ?= http://localhost:8000/mcp

# Build platform (force linux/amd64 for consistent builds across host architectures)
PLATFORM ?= linux/amd64

# Guard: ensure a container runtime was found
ifeq ($(CONTAINER_RUNTIME),)
    $(error No container runtime found. Install podman or docker.)
endif

# Podman-specific flags for user namespace mapping
ifeq ($(findstring podman,$(CONTAINER_RUNTIME)),podman)
    USERNS_FLAGS := --userns=keep-id
else
    USERNS_FLAGS :=
endif

.PHONY: help build build-no-cache run run-dev stop logs shell clean info
.PHONY: dev install sync test lint format check

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "Navigator Orchestrator - Development & Container Management"
	@echo ""
	@echo "Detected runtime: $(CONTAINER_RUNTIME)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@grep -E '^(dev|install|sync|test|lint|format|check):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Container:"
	@grep -E '^(build|run|stop|logs|shell|clean|info):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Development (uv)
# =============================================================================

dev: install ## Setup development environment
	@echo "Development environment ready!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'uv run python -m navigator_orchestrator' to run the server"

install: ## Install package in development mode
	uv sync

sync: ## Sync dependencies without installing dev packages
	uv sync --no-dev

test: ## Run all tests
	uv run pytest tests/ -q

lint: ## Run linter (ruff)
	uv run ruff check src/ tests/

format: ## Format code (ruff)
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

check: lint ## Run all checks

# =============================================================================
# Build
# =============================================================================

build: ## Build the container image
	DOCKER_DEFAULT_PLATFORM=$(PLATFORM) $(CONTAINER_RUNTIME) build --platform=$(PLATFORM) -f Containerfile -t $(FULL_IMAGE) .

build-no-cache: ## Build the container image without cache
	DOCKER_DEFAULT_PLATFORM=$(PLATFORM) $(CONTAINER_RUNTIME) build --platform=$(PLATFORM) -f Containerfile --no-cache -t $(FULL_IMAGE) .

# =============================================================================
# Run (Container)
# =============================================================================

run: ## Run the orchestrator container
	$(CONTAINER_RUNTIME) run --rm --name $(CONTAINER_NAME) \
		$(USERNS_FLAGS) \
		-p $(PORT):8001 \
		-e ORCHESTRATOR_RHOAI_MCP_URL=$(RHOAI_MCP_URL) \
		$(FULL_IMAGE)

run-dev: ## Run with debug logging
	$(CONTAINER_RUNTIME) run --rm --name $(CONTAINER_NAME) \
		$(USERNS_FLAGS) \
		-p $(PORT):8001 \
		-e ORCHESTRATOR_RHOAI_MCP_URL=$(RHOAI_MCP_URL) \
		-e LOG_LEVEL=DEBUG \
		$(FULL_IMAGE)

# =============================================================================
# Run (Local Development)
# =============================================================================

run-local: ## Run server locally (not in container)
	uv run python -m navigator_orchestrator

# =============================================================================
# Management
# =============================================================================

stop: ## Stop the running container
	-$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) 2>/dev/null || true
	-$(CONTAINER_RUNTIME) rm $(CONTAINER_NAME) 2>/dev/null || true

logs: ## View container logs
	$(CONTAINER_RUNTIME) logs -f $(CONTAINER_NAME)

shell: ## Open a shell in the running container
	$(CONTAINER_RUNTIME) exec -it $(CONTAINER_NAME) /bin/bash

clean: stop ## Remove container and image
	-$(CONTAINER_RUNTIME) rmi $(FULL_IMAGE) 2>/dev/null || true

clean-dev: ## Clean development artifacts
	rm -rf .venv dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# Info
# =============================================================================

info: ## Show configuration
	@echo "IMAGE:     $(FULL_IMAGE)"
	@echo "CONTAINER: $(CONTAINER_NAME)"
	@echo "RUNTIME:   $(CONTAINER_RUNTIME)"
	@echo "PORT:      $(PORT)"
	@echo "RHOAI_MCP: $(RHOAI_MCP_URL)"
