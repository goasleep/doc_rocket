# =============================================================================
# Docker-based Development Environment
# All operations run inside containers - no local dependencies needed
# =============================================================================

.PHONY: help build up down logs shell test lint format generate-client clean

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# =============================================================================
# Environment Setup
# =============================================================================

help: ## Show this help message
	@echo "$(BLUE)Docker Development Environment$(NC)"
	@echo "=============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

.env: ## Create .env file from example if not exists
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(RED)Please edit .env with your configuration!$(NC)"; \
	fi

# =============================================================================
# Build & Infrastructure
# =============================================================================

build: .env ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker compose build

build-backend: .env ## Build backend image only
	@echo "$(BLUE)Building backend image...$(NC)"
	docker compose build backend

build-frontend: .env ## Build frontend image only
	@echo "$(BLUE)Building frontend image...$(NC)"
	docker compose build frontend

rebuild: .env ## Rebuild all images (no cache)
	@echo "$(BLUE)Rebuilding Docker images (no cache)...$(NC)"
	docker compose build --no-cache

# =============================================================================
# Development - Start/Stop
# =============================================================================

up: .env ## Start all services in detached mode
	@echo "$(GREEN)Starting development environment...$(NC)"
	docker compose up -d

dev: .env ## Start with live-reload (docker compose watch)
	@echo "$(GREEN)Starting development environment with watch mode...$(NC)"
	docker compose watch

stop: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker compose stop

down: ## Stop and remove containers
	@echo "$(YELLOW)Stopping and removing containers...$(NC)"
	docker compose down

down-volumes: ## Stop and remove containers + volumes (WARNING: data loss)
	@echo "$(RED)Stopping and removing containers + volumes...$(NC)"
	@read -p "Are you sure? This will delete all data! [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
	fi

restart: down up ## Restart all services

# =============================================================================
# Logs & Debugging
# =============================================================================

logs: ## Show logs from all services
	docker compose logs -f

logs-backend: ## Show backend logs
	docker compose logs -f backend

logs-frontend: ## Show frontend logs
	docker compose logs -f frontend

logs-celery: ## Show celery worker logs
	docker compose logs -f celery-worker

ps: ## Show running containers
	docker compose ps

status: ## Check service health
	@echo "$(BLUE)Checking service status...$(NC)"
	@echo "Backend: $$(curl -s http://localhost:8000/api/v1/utils/health-check/ 2>/dev/null || echo '$(RED)DOWN$(NC)')"
	@echo "Frontend: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/ 2>/dev/null || echo '$(RED)DOWN$(NC)')"

# =============================================================================
# Shell Access
# =============================================================================

shell-backend: ## Open shell in backend container
	docker compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend sh

shell-mongodb: ## Open mongodb shell
	docker compose exec mongodb mongosh

shell-redis: ## Open redis cli
	docker compose exec redis redis-cli

# =============================================================================
# Testing (All run inside containers)
# =============================================================================

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests in container
	@echo "$(BLUE)Running backend tests...$(NC)"
	docker compose exec backend bash scripts/tests-start.sh

test-backend-watch: ## Run backend tests in watch mode
	@echo "$(BLUE)Running backend tests (watch mode)...$(NC)"
	docker compose exec backend uv run pytest -f

test-frontend: ## Run frontend E2E tests
	@echo "$(BLUE)Running frontend E2E tests...$(NC)"
	docker compose exec frontend pnpm exec playwright test

test-smoke: ## Run full-stack UI smoke test (requires dev environment up)
	@echo "$(BLUE)Seeding smoke test data...$(NC)"
	docker compose exec backend bash -c "cd /app/backend && uv run python scripts/seed-smoke-draft.py"
	@echo "$(BLUE)Running smoke tests in container...$(NC)"
	docker compose exec frontend pnpm exec playwright test smoke.spec.ts

test-frontend-ui: ## Run frontend E2E tests in UI mode
	@echo "$(BLUE)Running frontend E2E tests (UI mode)...$(NC)"
	docker compose exec frontend pnpm exec playwright test --ui

# =============================================================================
# Code Quality (All run inside containers)
# =============================================================================

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Run backend linting (mypy + ruff)
	@echo "$(BLUE)Running backend lint...$(NC)"
	docker compose exec backend bash scripts/lint.sh

lint-frontend: ## Run frontend linting (biome)
	@echo "$(BLUE)Running frontend lint...$(NC)"
	docker compose exec frontend pnpm run lint

format: format-backend format-frontend ## Format all code

format-backend: ## Format backend code (ruff)
	@echo "$(BLUE)Formatting backend code...$(NC)"
	docker compose exec backend bash scripts/format.sh

format-frontend: ## Format frontend code (biome)
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	docker compose exec frontend pnpm run format

check: ## Run all checks (lint + test)
	@echo "$(BLUE)Running all checks...$(NC)"
	$(MAKE) lint
	$(MAKE) test

# =============================================================================
# Code Generation (All run inside containers)
# =============================================================================

generate-client: ## Generate OpenAPI client (backend -> frontend)
	@echo "$(BLUE)Generating OpenAPI client...$(NC)"
	@docker compose exec backend bash -c 'cd /app && uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))"' > /tmp/openapi.json
	@mv /tmp/openapi.json frontend/openapi.json
	@docker compose exec frontend pnpm run generate-client
	@echo "$(GREEN)Client generated successfully!$(NC)"

generate-routes: ## Generate TanStack Router routes
	@echo "$(BLUE)Generating router routes...$(NC)"
	docker compose exec frontend pnpm run generate-routes

# =============================================================================
# Database Operations
# =============================================================================

db-migrate: ## Run database migrations (if any)
	@echo "$(BLUE)Running database setup...$(NC)"
	docker compose exec backend bash scripts/prestart.sh

db-seed: ## Seed database with initial data
	@echo "$(BLUE)Seeding database...$(NC)"
	docker compose exec backend uv run python -c "from app.core.db import seed_superuser; import asyncio; asyncio.run(seed_superuser())"

db-shell: ## Open MongoDB shell
	docker compose exec mongodb mongosh app

db-dump: ## Dump database to backup
	@echo "$(BLUE)Dumping database...$(NC)"
	@mkdir -p backups
	docker compose exec mongodb mongodump --out /data/backup/$(shell date +%Y%m%d_%H%M%S)
	@echo "$(GREEN)Database dumped to backups/$(shell date +%Y%m%d_%H%M%S)$(NC)"

# =============================================================================
# Package Management (All run inside containers)
# =============================================================================

add-backend: ## Add Python package (usage: make add-backend PACKAGE=requests)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)Error: PACKAGE is required. Usage: make add-backend PACKAGE=requests$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Adding $(PACKAGE) to backend...$(NC)"
	docker compose exec backend uv add $(PACKAGE)

dev-backend: ## Add Python dev package (usage: make dev-backend PACKAGE=pytest)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)Error: PACKAGE is required. Usage: make dev-backend PACKAGE=pytest$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Adding $(PACKAGE) to backend dev dependencies...$(NC)"
	docker compose exec backend uv add --dev $(PACKAGE)

add-frontend: ## Add npm package (usage: make add-frontend PACKAGE=lodash)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)Error: PACKAGE is required. Usage: make add-frontend PACKAGE=lodash$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Adding $(PACKAGE) to frontend...$(NC)"
	docker compose exec frontend pnpm add $(PACKAGE)

dev-frontend: ## Add npm dev package (usage: make dev-frontend PACKAGE=@types/lodash)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)Error: PACKAGE is required. Usage: make dev-frontend PACKAGE=@types/lodash$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Adding $(PACKAGE) to frontend dev dependencies...$(NC)"
	docker compose exec frontend pnpm add -D $(PACKAGE)

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Remove build artifacts and temporary files
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: down-volumes clean ## Full cleanup including volumes
	docker system prune -f

# =============================================================================
# Utilities
# =============================================================================

update: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	docker compose exec backend uv sync --upgrade
	docker compose exec frontend pnpm update

install-hooks: ## Install git hooks (if using pre-commit)
	@echo "$(BLUE)Installing git hooks...$(NC)"
	docker compose exec backend uv run pre-commit install

# =============================================================================
# Deployment
# =============================================================================

docker-push: ## Build and push Docker images
	@echo "$(BLUE)Building and pushing Docker images...$(NC)"
	docker compose build
	docker compose push
