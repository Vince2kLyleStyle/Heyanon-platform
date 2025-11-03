import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine
from .logging_setup import init_logging
from .middleware_request_id import request_id_middleware
from . import models
from .routes_ingest import router as ingest_router
from .routes_read import router as read_router
from .routes_metrics import router as metrics_router
from .routes_copy import router as copy_router
from .middleware import metrics_middleware

app = FastAPI(title="HeyAnon API", version="0.1.0")

# initialize structured logging
init_logging()

# register request-id middleware early so downstream logs can use it
app.middleware("http")(request_id_middleware)

# register metrics middleware early
app.middleware("http")(metrics_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wait for Postgres to be ready before creating tables to avoid startup races.
# Try a few times with a short backoff; if it still fails, allow the app to start
# so healthchecks and other services can report, but log the error.
import time
from sqlalchemy.exc import OperationalError

max_retries = 12
for attempt in range(1, max_retries + 1):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError as e:
        if attempt == max_retries:
            # Last attempt: re-raise so it's visible in logs
            raise
        print(f"Database not ready (attempt {attempt}/{max_retries}): {e}")
        time.sleep(2)

@app.get("/health")
def health():
    return {"ok": True}

# Routers
app.include_router(ingest_router)
app.include_router(read_router)
app.include_router(metrics_router)
app.include_router(copy_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)