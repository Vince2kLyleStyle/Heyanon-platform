Copy-trade Phase 1 executor

This is a small paper-execution skeleton. It polls the API for subscribers and recent trades and prints what it would execute.

How to enable (development):
- In infra/docker-compose.yml the service `copy-executor` is added with DISABLE_COPY=1 by default.
- To enable change the environment variable to DISABLE_COPY=0 and restart the service:
  docker compose up -d copy-executor

Notes:
- The executor is intentionally simple: it does not perform real fills. It prints intentions and posts execution records to the API via POST /v1/copy/executions (which is implemented).
- Next steps: implement risk sizing, idempotent fills, retry/backoff and a real broker adapter for paper fills.
