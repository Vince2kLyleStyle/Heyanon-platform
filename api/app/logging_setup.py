import logging
import json
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "logger": record.name,
        }
        # allow message to be a dict encoded as string
        try:
            msg = record.getMessage()
            # if it's already a JSON string representing an object, try to load
            try:
                parsed = json.loads(msg)
                if isinstance(parsed, dict):
                    payload.update(parsed)
                else:
                    payload["msg"] = msg
            except Exception:
                payload["msg"] = msg
        except Exception:
            payload["msg"] = str(record.msg)

        return json.dumps(payload)


def init_logging(level: int = logging.INFO):
    root = logging.getLogger()
    # don't add duplicate handlers
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        # replace existing handlers' formatters
        for h in root.handlers:
            h.setFormatter(JSONFormatter())
        root.setLevel(level)
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.handlers = [handler]
    root.setLevel(level)
