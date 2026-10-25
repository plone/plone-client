"""Unit tests for logging configuration."""

from __future__ import annotations

from plone_client.logging_config import set_logger
from plone_client.logging_config import setup_logging

import logging
import pytest


@pytest.mark.unit
class TestLogging:
    def test_setup_logging_sets_level(self) -> None:
        setup_logging(level=logging.DEBUG)
        import plone_client.logging_config as lc

        assert lc.logger.level == logging.DEBUG

    def test_setup_logging_accepts_string(self) -> None:
        setup_logging(level="INFO")
        import plone_client.logging_config as lc

        assert lc.logger.level == logging.INFO

    def test_set_logger_replaces_logger(self) -> None:
        import plone_client.logging_config as lc

        original = lc.logger
        custom = logging.getLogger("my_app.plone")
        set_logger(custom)
        assert lc.logger is custom
        # Restore
        set_logger(original)

    def test_custom_handler_used(self) -> None:
        handler = logging.NullHandler()
        setup_logging(level=logging.DEBUG, handler=handler)
        import plone_client.logging_config as lc

        assert handler in lc.logger.handlers
