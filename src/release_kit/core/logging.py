"""Structured logging via structlog.

The whole runtime logs through this module so dry-run and apply
paths share an audit trail. Sensitive values are redacted in
``redact_token`` before any log statement that could leak them.

Public surface:

- ``get_logger(name)``    bound logger
- ``redact_token(value)`` redacts the middle of a token, keeps
                          a useful 4-char prefix for tracking
- ``configure(level)``    one-time setup; called by the CLI on start
"""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog


def configure(level: str = "INFO", *, json: bool = False) -> None:
    """
    Configure structlog + stdlib logging for the process.

    Idempotent; safe to call more than once. JSON output is for CI
    integration (machine-parseable); human output is the default.

    @param  level  logging level name (DEBUG/INFO/WARNING/ERROR).
    @param  json   render as JSON one-event-per-line.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a bound structlog logger. Use module-name conventions:
    ``logger = get_logger(__name__)``.

    @param  name  module identifier.
    @return BoundLogger
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


def redact_token(value: str | None, *, prefix_chars: int = 4) -> str:
    """
    Redact a token for safe logging.

    Keeps the first ``prefix_chars`` characters and a length hint so
    you can still tell two tokens apart in logs without leaking the
    full secret.

    Examples::

        redact_token("pypi-AgEIabcdef1234")
        # -> "pypi***(len=17)"

        redact_token("ghp_1234567890abcdef", prefix_chars=8)
        # -> "ghp_1234***(len=20)"

    @param  value          the secret (None / empty returns "").
    @param  prefix_chars   how many leading chars to keep.
    @return                redacted string.
    """
    if not value:
        return ""
    if len(value) <= prefix_chars:
        return "***"
    return f"{value[:prefix_chars]}***(len={len(value)})"
