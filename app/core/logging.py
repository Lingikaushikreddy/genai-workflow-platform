import logging
from contextvars import ContextVar
import json

request_id_var: ContextVar[str] = ContextVar("request_id", default="<none>")

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "name": record.name
        }
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "status"):
            log_obj["status"] = record.status
        if hasattr(record, "mock_mode"):
            log_obj["mock_mode"] = record.mock_mode
        return json.dumps(log_obj)

def setup_logging(level_name: str):
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(JSONFormatter())
        logger.addHandler(ch)
