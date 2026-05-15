"""Tests for the run-command + report primitives."""

from __future__ import annotations

import pytest

from release_kit.core.errors import ReleaseKitError
from release_kit.core.runner import (
    RunContext,
    RunReport,
    StepOutcome,
    run_command,
)


def test_run_command_dry_run_returns_none() -> None:
    """Dry-run must NOT invoke subprocess and must return None."""
    result = run_command(["echo", "would-not-print"], dry_run=True)
    assert result is None


def test_run_command_apply_runs() -> None:
    """Apply path invokes subprocess and returns CompletedProcess."""
    result = run_command(["echo", "hello"], dry_run=False)
    assert result is not None
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_run_command_nonzero_exit_raises() -> None:
    """check=True (default) raises on nonzero exit."""
    with pytest.raises(ReleaseKitError, match="command failed"):
        run_command(["sh", "-c", "exit 7"], dry_run=False)


def test_run_command_check_false_returns_completed() -> None:
    """check=False returns the CompletedProcess instead of raising."""
    result = run_command(["sh", "-c", "exit 3"], dry_run=False, check=False)
    assert result is not None
    assert result.returncode == 3


def test_run_command_empty_argv_rejected() -> None:
    with pytest.raises(ValueError, match="argv cannot be empty"):
        run_command([], dry_run=True)


def test_run_command_timeout_raises() -> None:
    with pytest.raises(ReleaseKitError, match="timed out"):
        run_command(["sh", "-c", "sleep 10"], dry_run=False, timeout=0.1)


def test_run_report_summary_clean() -> None:
    r = RunReport()
    r.target_outcomes["pypi"] = [
        StepOutcome("authenticate", "ok"),
        StepOutcome("publish", "dry-run"),
    ]
    assert "targets: 1" in r.summary()
    assert "dry-run: 1" in r.summary()
    assert "ok" in r.summary()
    assert r.ok is True


def test_run_report_with_failure() -> None:
    fail = StepOutcome("publish", "failed", "rejected by server")
    r = RunReport()
    r.target_outcomes["pypi"] = [fail]
    r.failures.append(fail)
    assert r.ok is False
    assert "failed: 1" in r.summary()


def test_run_context_carries_policy_view() -> None:
    """RunContext is a value object the runner injects into each step."""
    from release_kit.core.config import PolicyConfig
    ctx = RunContext(
        dry_run=True,
        policies=PolicyConfig(allow_token_auth=True),
        target_name="pypi",
    )
    assert ctx.dry_run is True
    assert ctx.policies.allow_token_auth is True
    assert ctx.target_name == "pypi"
