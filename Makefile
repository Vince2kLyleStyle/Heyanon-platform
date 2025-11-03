# Development Makefile helpers

.PHONY: db-up prometheus-up api-up all

.PHONY: bots-up

# Run alembic migrations inside the api container (requires api built with alembic files copied)
db-up:
	@echo "Running DB migrations (alembic -c /app/alembic.ini upgrade head)"
	docker compose exec api sh -lc "alembic -c /app/alembic.ini upgrade head"

prometheus-up:
	@echo "Starting Prometheus, Alertmanager and Discord relay"
	docker compose up -d --build prometheus alertmanager discord-relay

api-up:
	@echo "Starting API, web and copy-executor"
	docker compose up -d --build api web copy-executor

bots-up:
	@echo "Starting bots via infra/multi-bot-runner.ps1"
	@powershell -NoProfile -ExecutionPolicy Bypass -File infra/multi-bot-runner.ps1 -DryRun:$false

all: prometheus-up api-up db-up
