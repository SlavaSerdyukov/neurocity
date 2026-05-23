from __future__ import annotations

import logging


class UvicornNoiseFilter(logging.Filter):
    """Hide routine browser cache and websocket reconnect noise from dev logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if message in {"connection open", "connection closed"}:
            return False
        if "GET /static/" in message and (" 304 " in message or " 200 " in message):
            return False
        if "GET /favicon.ico" in message:
            return False
        return True


def configure_logging() -> None:
    noise_filter = UvicornNoiseFilter()
    for logger_name in ("uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        if not any(isinstance(item, UvicornNoiseFilter) for item in logger.filters):
            logger.addFilter(noise_filter)

