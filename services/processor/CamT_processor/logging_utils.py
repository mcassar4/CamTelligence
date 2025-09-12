import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "time": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
        }
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            base["stack"] = self.formatStack(record.stack_info)
        if hasattr(record, "extra_payload"):
            base.update(getattr(record, "extra_payload"))
        return json.dumps(base, ensure_ascii=False)


def configure_logging(level: str | None = None) -> None:
    env_level = os.getenv("LOG_LEVEL")
    target = level or env_level or "INFO"
    logging_level = getattr(logging, target.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(
        level=logging_level,
        handlers=[handler],
        force=True,
    )


def log_span(logger: logging.Logger, label: str, **kwargs: Any):
    logger.info(label, extra={"extra_payload": kwargs})
