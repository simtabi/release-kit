"""Logging must follow sys.stderr, not keep the stream that was current at configure time."""

from __future__ import annotations

import io
import sys

import pytest

from release_kit.core.logging import configure, get_logger


def test_logging_survives_the_configured_stream_being_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    # A harness swaps stderr, the CLI configures logging, the harness closes its stream.
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stderr", captured)
    configure("INFO")
    get_logger("first").info("into the temporary stream")
    captured.close()
    monkeypatch.undo()

    # The next log call must reach the current stderr, not the closed one.
    replacement = io.StringIO()
    monkeypatch.setattr(sys, "stderr", replacement)
    get_logger("second").info("after the swap")

    assert "after the swap" in replacement.getvalue()
