from fastapi import Request


def limit_key_from_request(request: Request) -> str:
    # Prefer API key identity if present; use Authorization or X-API-Key headers
    api_key = None
    if request.headers.get("Authorization"):
        api_key = request.headers.get("Authorization")
    elif request.headers.get("X-API-Key"):
        api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"ak:{api_key}"
    # fallback to client IP if available
    host = None
    try:
        host = request.client.host if request.client else None
    except Exception:
        host = None
    return f"ip:{host or 'unknown'}"
