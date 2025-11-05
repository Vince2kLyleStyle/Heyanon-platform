from fastapi import Request
from pathlib import Path
import json
from typing import Dict, Any, List


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


# ===== File-based persistence utilities =====

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """Append a JSON object as a new line to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":")) + "\n")


def tail_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    """Read last N lines from a JSONL file, return as list (newest first)."""
    if not path.exists():
        return []
    
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        lines = lines[-limit:]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return list(reversed(out))  # Newest first
    except Exception:
        return []


def write_state(path: Path, state_dict: Dict[str, Any]) -> None:
    """Write a state dictionary as JSON (overwrites file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state_dict, indent=2), encoding="utf-8")


def read_state(path: Path) -> Dict[str, Any]:
    """Read state JSON file, return empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
