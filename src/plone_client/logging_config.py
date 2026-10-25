"""
Logging utilities for plone-client.

The library uses a single named logger (``plone_client``).  By default it
ships with a NullHandler so it stays silent unless the application
configures logging.  Call :func:`setup_logging` for a quick console setup,
or replace the logger entirely via :func:`set_logger`.
"""

from __future__ import annotations

from typing import Any

import logging
import sys


# Library-wide logger - consumers can fetch it with logging.getLogger("plone_client")
logger: logging.Logger = logging.getLogger("plone_client")
logger.addHandler(logging.NullHandler())


def setup_logging(
    level: int | str = logging.WARNING,
    handler: logging.Handler | None = None,
    formatter: logging.Formatter | None = None,
) -> None:
    """
    Configure the ``plone_client`` logger for console output.

    :param level: Logging level (e.g. ``logging.DEBUG`` or ``"DEBUG"``).
    :type level: int or str
    :param handler: Custom handler.  Defaults to
        :class:`logging.StreamHandler` (stdout).
    :type handler: logging.Handler or None
    :param formatter: Custom formatter.  Defaults to a simple timestamped format.
    :type formatter: logging.Formatter or None
    """
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    if handler is None:
        handler = logging.StreamHandler(sys.stdout)

    if formatter is None:
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicate output
    logger.handlers.clear()
    logger.addHandler(handler)


def set_logger(custom_logger: logging.Logger) -> None:
    """
    Replace the library logger entirely.

    Useful when the host application already has a configured logger and
    wants plone-client to emit through the same pipeline.

    :param custom_logger: Any :class:`logging.Logger` instance.
    :type custom_logger: logging.Logger

    >>> import logging
    >>> from plone_client.logging_config import set_logger
    >>> set_logger(logging.getLogger("myapp"))
    """
    global logger
    logger = custom_logger


class RequestLogger:
    """
    Mixin / helper that provides structured request/response logging.

    Attach to the connection layer to get consistent DEBUG output for
    every HTTP call without cluttering application code.
    """

    def log_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> None:
        logger.debug("→ %s %s  params=%s", method.upper(), url, kwargs.get("params"))

    def log_response(
        self,
        method: str,
        url: str,
        status_code: int,
        elapsed_ms: float,
    ) -> None:
        logger.debug(
            "← %s %s  status=%d  elapsed=%.1fms",
            method.upper(),
            url,
            status_code,
            elapsed_ms,
        )

    def log_retry(self, attempt: int, max_retries: int, reason: str) -> None:
        logger.warning("Retry %d/%d for reason: %s", attempt, max_retries, reason)
