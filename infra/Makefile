dev:
	# start api and bot in dev mode (uses docker-compose.override.yml)
	docker compose up -d --build api bot

logs:
	docker compose logs -f api bot

e2e:
	python e2e_test.py

prod:
	# production start (explicitly uses main compose file)
	docker compose -f docker-compose.yml up -d --build api bot

# DB migration helpers (run from infra/)
db-init:
	@echo "Initializing alembic inside api container (ok if already present)..."
	docker compose exec api sh -lc "alembic init alembic || true"

# Usage: make db-migrate MSG="add_table_x"
db-migrate:
	@if [ -z "$(MSG)" ]; then echo "Please set MSG=\"my message\""; exit 1; fi
	@echo "Creating alembic migration with message: $(MSG)"
	docker compose exec api sh -lc "alembic revision --autogenerate -m \"$(MSG)\""

db-upgrade:
	@echo "Applying alembic migrations (upgrade head)..."
	docker compose exec api sh -lc "alembic upgrade head"
