import logging
import os
import time

from ..config.janitor_settings import JanitorSettings
from .retention import cleanup_retention
from ..logging_utils import configure_logging


def setup_logging() -> None:
    configure_logging(os.getenv("LOG_LEVEL"))


def run_once(settings: JanitorSettings) -> None:
    if not settings.retention_enabled:
        logging.info("Retention janitor disabled; skipping run")
        return
    logging.info("Starting retention cleanup", extra={"extra_payload": {"retention_days": settings.retention_days}})
    counts = cleanup_retention(settings)
    logging.info("Retention cleanup finished", extra={"extra_payload": counts})


def main() -> None:
    setup_logging()
    settings = JanitorSettings()
    interval = max(60, settings.retention_interval_seconds)
    while True:
        run_once(settings)
        time.sleep(interval)


if __name__ == "__main__":
    main()
