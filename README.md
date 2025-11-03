HeyAnon Platform (local dev)

Quick start (PowerShell / Windows):

# From the infra folder
cd infra

docker compose build api web bot

docker compose up -d postgres redis
# wait until postgres is ready (check logs), then start api
docker compose up -d api

# Seed DB (runs inside the api container)
docker compose exec api sh -c "python -m app.scripts.seed_strategies"

# Start the web and bot
docker compose up -d web bot

Verify:
- API health: http://localhost:8000/health
- Web UI: http://localhost:3000
- Seeded strategies: http://localhost:8000/v1/strategies

If you want to run the bot locally without compose, set environment variables from `bot/.env.example` and run:
python bot.py

