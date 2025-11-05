.PHONY: help install run test fmt lint clean docker-build docker-up docker-down

help:
	@echo "Mico API - Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run API locally (port 8000)"
	@echo "  make test         - Run tests"
	@echo "  make fmt          - Format code"
	@echo "  make lint         - Lint code"
	@echo "  make clean        - Clean cache and build artifacts"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/ -v

fmt:
	black app/ tests/
	isort app/ tests/

lint:
	ruff check app/ tests/
	mypy app/ --ignore-missing-imports

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache

docker-build:
	docker-compose -f ../infra/docker-compose.yml build api

docker-up:
	docker-compose -f ../infra/docker-compose.yml up -d

docker-down:
	docker-compose -f ../infra/docker-compose.yml down
