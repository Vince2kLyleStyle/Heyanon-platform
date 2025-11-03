HeyAnon Bot (starter)

This folder contains a minimal example bot that posts position snapshots to the HeyAnon API.

How to run with Docker Compose (recommended):
- From the `infra/` folder run the compose commands.

Or build the bot image directly for faster iteration:

# Build image
# docker build -t heyanon_bot:local .

# Run container (example, pass envs)
# docker run --rm --env HEYANON_API_KEY=dev_api_key_change_me --env BASE_URL=http://host.docker.internal:8000 heyanon_bot:local

Configuration:
- Copy `.env.example` to `.env` and edit values, or pass envs via Docker/Compose.
- `SEND_TEST_TRADE=1` will post a single test trade on startup.
- `SNAPSHOT_INTERVAL_SEC` controls how often the bot sends position snapshots.

Notes:
- This is a starter bot; replace `bot.py` with your trading logic. The client class `HeyAnon` performs simple POST requests to the API endpoints.
