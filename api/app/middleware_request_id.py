import time
import uuid
import json
import logging
from typing import Callable
from fastapi import Request, Response

log = logging.getLogger("api")


async def request_id_logging_middleware(request: Request, call_next: Callable):
    # extract or create request id
    rid = request.headers.get("X-Request-Id") or request.headers.get("X-Request-Id".lower()) or str(uuid.uuid4())
    # attach to request.state for downstream usage
    request.state.request_id = rid
    t0 = time.perf_counter()
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise
    finally:
        dt = (time.perf_counter() - t0) * 1000.0
        rec = {
            "ts": int(time.time() * 1000),
            "level": "info",
            "service": "api",
            "path": request.url.path,
            "method": request.method,
            "status": status_code,
            "latency_ms": round(dt, 2),
            "request_id": rid,
            "user_agent": request.headers.get("user-agent", ""),
            "ip": request.client.host if request.client else None,
        }
        # emit JSON log on standard logger
        try:
            log.info(json.dumps(rec))
        except Exception:
            log.info(rec)
    return response
import uuid
import logging
from fastapi import Request

logger = logging.getLogger("api.request")


async def request_id_middleware(request: Request, call_next):
    # Get or generate request id
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = rid
    # Call next and capture response
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        status = response.status_code
    except Exception as e:
        # ensure header on exceptions
        # re-raise after logging
        logger.exception({"event": "exception", "request_id": rid})
        raise
    finally:
        pass

    # structured access log
    try:
        remote = request.client.host if request.client else "unknown"
    except Exception:
        remote = "unknown"
    latency_ms = None
    # we don't measure latency here; metrics middleware handles it. Include minimal info.
    logger.info({
        "event": "http_req",
        "service": "api",
        "method": request.method,
        "path": request.url.path,
        "status": status,
        "remote_ip": remote,
        "request_id": rid,
    })

    return response
