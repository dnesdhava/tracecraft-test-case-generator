from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from .settings import Settings


class ContextFilter(logging.Filter):
    """Add correlation fields without placing source content in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = getattr(record, "run_id", "")
        record.source_id = getattr(record, "source_id", "")
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "run_id": getattr(record, "run_id", ""),
            "source_id": getattr(record, "source_id", ""),
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(settings: Settings) -> None:
    logger = logging.getLogger("tcg")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if settings.log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] run=%(run_id)s %(message)s")
        )
    logger.addHandler(handler)
    logger.propagate = False
