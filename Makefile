.PHONY: start stop restart logs migrate migrate-down shell-backend shell-db build clean help

# ─── Docker ───────────────────────────────────────────────────────
start:
	@echo "Starting JARVIS..."
	docker compose up -d
	@echo "JARVIS is online."
	@echo "  Frontend : http://localhost:3000"
	@echo "  Backend  : http://localhost:8000/docs"
	@echo "  n8n      : http://localhost:5678"

stop:
	@echo "Stopping JARVIS..."
	docker compose down

restart:
	docker compose down && docker compose up -d

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-db:
	docker compose logs -f postgres

build:
	docker compose build --no-cache

clean:
	docker compose down -v --remove-orphans
	@echo "All containers and volumes removed."

# ─── Database ─────────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migrate-down:
	docker compose exec backend alembic downgrade -1

migrate-create:
	@read -p "Migration name: " name; \
	docker compose exec backend alembic revision --autogenerate -m "$$name"

# ─── Shells ───────────────────────────────────────────────────────
shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER:-jarvis} -d $${POSTGRES_DB:-jarvis_db}

shell-redis:
	docker compose exec redis redis-cli -a $${REDIS_PASSWORD:-redis_secret}

# ─── Help ─────────────────────────────────────────────────────────
help:
	@echo "JARVIS Makefile commands:"
	@echo "  make start          — Start all services"
	@echo "  make stop           — Stop all services"
	@echo "  make restart        — Restart all services"
	@echo "  make logs           — Stream all logs"
	@echo "  make logs-backend   — Stream backend logs"
	@echo "  make migrate        — Run DB migrations"
	@echo "  make migrate-down   — Rollback last migration"
	@echo "  make migrate-create — Create a new migration"
	@echo "  make build          — Rebuild all images"
	@echo "  make clean          — Remove all containers + volumes"
	@echo "  make shell-backend  — Bash into backend container"
	@echo "  make shell-db       — psql into postgres container"
