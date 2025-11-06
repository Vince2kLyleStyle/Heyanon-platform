# MICO Signals API - Production Backend

Clean, production-ready FastAPI backend for website signals. No Telegram/Discord/Sheets. CoinGecko data for BTC, SOL, PUMP.

## Quick Test

\\\ash
curl http://localhost:8000/healthz
curl http://localhost:8000/v1/summary
curl http://localhost:8000/v1/signals
\\\

## Endpoints

- **GET /healthz** - Health check with cache age
- **GET /v1/summary** - Quick regime + status
- **GET /v1/signals** - Full signals for BTC, SOL, PUMP

## Running Locally

\\\ash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
\\\

## Render Deployment

- Build: \pip install -r requirements.txt\
- Start: \uvicorn main:app --host 0.0.0.0 --port \\
- Env vars: \CACHE_TTL_SEC=60\, \API_ORIGINS=https://your-site.com\

See full docs in repo README.
