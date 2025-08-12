.PHONY: help build up down logs test clean lint format type-check

# Default target
help:
	@echo "FS Reconciliation Agents - Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make build     - Build all Docker images"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - View logs from all services"
	@echo "  make restart   - Restart all services"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run all tests"
	@echo "  make test-unit - Run unit tests only"
	@echo "  make test-int  - Run integration tests only"
	@echo "  make test-e2e  - Run end-to-end tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint      - Run linting checks"
	@echo "  make format    - Format code with black and isort"
	@echo "  make type-check - Run type checking with mypy"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate - Run database migrations"
	@echo "  make db-reset   - Reset database (WARNING: destructive)"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-local    - Deploy to local environment"
	@echo "  make deploy-prod     - Deploy to production environment"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean     - Clean up Docker resources"
	@echo "  make shell     - Open shell in langgraph-agent container"
	@echo "  make api-shell - Open shell in api-service container"

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

# Testing commands
test:
	docker-compose exec langgraph-agent python -m pytest tests/ -v

test-unit:
	docker-compose exec langgraph-agent python -m pytest tests/unit/ -v

test-int:
	docker-compose exec langgraph-agent python -m pytest tests/integration/ -v

test-e2e:
	docker-compose exec langgraph-agent python -m pytest tests/e2e/ -v

# Code quality commands
lint:
	docker-compose exec langgraph-agent flake8 src/ tests/
	docker-compose exec langgraph-agent black --check src/ tests/
	docker-compose exec langgraph-agent isort --check-only src/ tests/

format:
	docker-compose exec langgraph-agent black src/ tests/
	docker-compose exec langgraph-agent isort src/ tests/

type-check:
	docker-compose exec langgraph-agent mypy src/

# Database commands
db-migrate:
	docker-compose exec langgraph-agent alembic upgrade head

db-reset:
	@echo "WARNING: This will destroy all data in the database!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose exec database psql -U reconciliation_user -d reconciliation_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
		docker-compose exec langgraph-agent alembic upgrade head; \
	fi

# Deployment commands
deploy-local:
	docker-compose -f deployment/local/docker-compose.yml up -d

deploy-prod:
	docker-compose -f docker-compose.prod.yml up -d

# Production commands
prod-deploy: ## Deploy production environment
	./scripts/deploy.sh

prod-optimize: ## Optimize production performance
	./scripts/optimize.sh

prod-logs: ## View production logs
	docker-compose -f docker-compose.prod.yml logs -f

prod-stop: ## Stop production environment
	docker-compose -f docker-compose.prod.yml down

prod-restart: ## Restart production services
	docker-compose -f docker-compose.prod.yml restart

# Testing commands
test-phase6: ## Run Phase 6 integration tests
	python3 scripts/test_phase6_integration.py

# Utility commands
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

shell:
	docker-compose exec langgraph-agent /bin/bash

api-shell:
	docker-compose exec api-service /bin/bash

# Development setup
setup-dev:
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make build && make up"

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "API service is not healthy"
	@curl -f http://localhost:80/ || echo "UI service is not healthy"
	@docker-compose exec database pg_isready -U reconciliation_user || echo "Database is not healthy"

# Performance monitoring
monitor:
	@echo "System resource usage:"
	@docker stats --no-stream
	@echo ""
	@echo "Container status:"
	@docker-compose ps

# Monitoring commands
monitor-dashboards: ## Open monitoring dashboards
	@echo "Opening monitoring dashboards..."
	@echo "Grafana: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "API Docs: http://localhost:8000/docs"

health-check: ## Check service health
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health || echo "API service not responding"
	@docker-compose exec database pg_isready -U fs_user || echo "Database not responding"
	@docker-compose exec redis redis-cli ping || echo "Redis not responding"

# Backup and restore
backup:
	@echo "Creating database backup..."
	docker-compose exec database pg_dump -U reconciliation_user reconciliation_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore:
	@echo "Restoring database from backup..."
	@read -p "Enter backup file name: " backup_file; \
	docker-compose exec -T database psql -U reconciliation_user -d reconciliation_db < $$backup_file
