from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
import aiohttp
from config import COINS, CACHE_TTL_SEC, DISABLE_SIGNALS, API_ORIGINS
from indicators import build_signals_snapshot, compute_regime

app = FastAPI(title="MICO Signals")

app.add_middleware(
    CORSMiddleware,
    allow_origins=API_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


class Cache:
    ts = 0
    data = None
    status = "ok"  # ok | degraded | paused
    errors = 0
    regime = "Neutral"


cache = Cache()


@app.on_event("startup")
async def startup():
    app.state.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))


@app.on_event("shutdown")
async def shutdown():
    await app.state.session.close()


@app.get("/v1/signals")
async def signals():
    now = time.time()
    if DISABLE_SIGNALS:
        return {
            "last_updated": cache.ts or int(now),
            "regime": cache.regime,
            "signals": cache.data or {},
            "status": "paused",
        }
    if cache.data and now - cache.ts < CACHE_TTL_SEC:
        return {
            "last_updated": cache.ts,
            "regime": cache.regime,
            "signals": cache.data,
            "status": cache.status,
        }
    try:
        regime = await compute_regime(app.state.session)
        signals = await build_signals_snapshot(app.state.session, COINS, regime)
        cache.ts = int(now)
        cache.data = signals
        cache.regime = regime
        cache.status = "ok"
        cache.errors = 0
        return {
            "last_updated": cache.ts,
            "regime": regime,
            "signals": signals,
            "status": "ok",
        }
    except Exception as e:
        cache.errors += 1
        cache.status = "degraded" if cache.errors < 3 else "degraded"
        return {
            "last_updated": cache.ts or int(now),
            "regime": cache.regime,
            "signals": cache.data or {},
            "status": cache.status,
            "error": str(e),
        }


@app.get("/v1/summary")
async def summary():
    now = time.time()
    if cache.data and now - cache.ts < CACHE_TTL_SEC:
        return {
            "updatedAt": cache.ts,
            "regime": cache.regime,
            "status": cache.status,
            "errors": cache.errors,
        }
    try:
        regime = await compute_regime(app.state.session)
        cache.regime = regime
        cache.ts = int(now)
        cache.status = "ok"
        cache.errors = 0
        return {
            "updatedAt": cache.ts,
            "regime": regime,
            "status": "ok",
            "errors": 0,
        }
    except Exception as e:
        cache.errors += 1
        cache.status = "degraded"
        return {
            "updatedAt": cache.ts or int(now),
            "regime": cache.regime,
            "status": cache.status,
            "errors": cache.errors,
        }


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "cache_age": int(time.time() - cache.ts) if cache.ts else None}
