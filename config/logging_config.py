"""Structured JSON logging configuration for LLM Service.

Provides a JSON formatter that emits log records as single-line JSON objects
with explicit fields: timestamp, level, event, source, request_id, duration_ms,
attempt, message, and any extra fields attached via logger.info(..., extra={...}).
"""

import json
import logging
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler

from config import settings

# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    # Fields that logging always injects – we expose them explicitly
    _core_fields = {"levelname", "name", "msg", "args", "exc_info", "stack_info"}

    def format(self, record: logging.LogRecord) -> str:
        # Build the base payload
        payload: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
        }

        # Extract request_id if present
        req_id = getattr(record, "request_id", None)
        if req_id:
            payload["request_id"] = req_id

        # Extract duration_ms if present
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms

        # Extract attempt number if present
        attempt = getattr(record, "attempt", None)
        if attempt is not None:
            payload["attempt"] = attempt

        # Extract source component if present
        source = getattr(record, "source", None)
        if source:
            payload["source"] = source

        # Extract event type if present
        event = getattr(record, "event", None)
        if event:
            payload["event"] = event

        # Build the message – merge format string + positional args
        msg = record.getMessage()
        payload["message"] = msg

        # Include any extra fields that were passed via logger.xxx(..., extra={...})
        for key, value in record.__dict__.items():
            if key in self._core_fields:
                continue
            if key.startswith("_"):
                continue
            # Skip fields already placed above
            if key in ("request_id", "duration_ms", "attempt", "source", "event"):
                continue
            if key == "message":
                continue
            if key == "asctime":
                continue
            if key == "created":
                continue
            if key == "relativeCreated":
                continue
            if key == "exc_text":
                continue
            if key == "stack_info":
                continue
            if key == "lineno":
                continue
            if key == "funcName":
                continue
            if key == "pathname":
                continue
            if key == "filename":
                continue
            if key == "module":
                continue
            if key == "exc_info":
                continue
            if key == "thread":
                continue
            if key == "threadName":
                continue
            if key == "process":
                continue
            if key == "processName":
                continue
            if key == "levelname":
                continue
            if key == "name":
                continue
            if key == "msg":
                continue
            if key == "args":
                continue
            if key == "levelno":
                continue
            # Include remaining extras (e.g. dish, people, cache_key, etc.)
            payload[key] = value

        # Preserve exception info as a string
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Request ID middleware / context helpers
# ---------------------------------------------------------------------------

def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with JSON formatting."""
    logger = logging.getLogger(name)
    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    formatter = JsonFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    log_file = settings.log_file
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Disable propagation to avoid duplicate logs when parent has handlers
    logger.propagate = False
    
    return logger


# ---------------------------------------------------------------------------
# Top-level logger instance (for convenience)
# ---------------------------------------------------------------------------

logger = get_logger("llm_service")
