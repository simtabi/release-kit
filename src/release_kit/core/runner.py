"""Dry-run + idempotency primitives.

Every platform's ``publish`` / ``bootstrap`` / ``rotate`` method
takes a :class:`RunContext`. The context carries:

- ``dry_run`` — whether to execute or just plan
- ``logger``  — bound structlog logger
- ``policies`` — read-only view of the active PolicyConfig

The :class:`Runner` class composes contexts across multiple targets
and collects per-target outcomes into a :class:`RunReport`.

Idempotency: each platform decides what "already done" looks like
(e.g., PyPI: version already on the registry). Platforms surface
that decision via :class:`StepOutcome.status` so the runner can
print a clean "skipped (already published)" message instead of an
error.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Literal

from .config import PolicyConfig
from .errors import ReleaseKitError
from .logging import get_logger

_log = get_logger(__name__)

StepStatus = Literal["ok", "skipped", "failed", "dry-run"]


@dataclass(frozen=True)
class StepOutcome:
    """
    Result of a single step inside a target's flow.

    @field  step      Human label ("preflight", "publish", "verify").
    @field  status    ``ok`` | ``skipped`` | ``failed`` | ``dry-run``.
    @field  detail    One-line summary surfaced to the user.
    @field  error     Optional underlying exception, when status=failed.
    """

    step: str
    status: StepStatus
    detail: str = ""
    error: BaseException | None = None


@dataclass
class RunContext:
    """
    The contract every platform consumes for one execution.

    Pass-by-value where possible; the runner injects this into each
    target's method call. Platforms should not mutate it.

    @field  dry_run   True = plan only, no external mutation.
    @field  policies  the active policy block from the loaded config.
    """

    dry_run: bool
    policies: PolicyConfig
    target_name: str = ""


@dataclass
class RunReport:
    """
    Aggregated outcome across one or more targets.

    The runner returns this from :py:meth:`Runner.execute`.

    @field  target_outcomes  per-target list of StepOutcomes, keyed by name.
    @field  failures         flat list of failed StepOutcomes for fast checks.
    """

    target_outcomes: dict[str, list[StepOutcome]] = field(default_factory=dict)
    failures: list[StepOutcome] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def summary(self) -> str:
        total = sum(len(v) for v in self.target_outcomes.values())
        skipped = sum(1 for v in self.target_outcomes.values() for s in v if s.status == "skipped")
        dry = sum(1 for v in self.target_outcomes.values() for s in v if s.status == "dry-run")
        parts = [
            f"targets: {len(self.target_outcomes)}",
            f"steps: {total}",
        ]
        if skipped:
            parts.append(f"skipped: {skipped}")
        if dry:
            parts.append(f"dry-run: {dry}")
        if self.failures:
            parts.append(f"failed: {len(self.failures)}")
        else:
            parts.append("ok")
        return "; ".join(parts)


# ---------------------------------------------------------------------------
# Subprocess wrapper
# ---------------------------------------------------------------------------


def run_command(
    argv: list[str],
    *,
    dry_run: bool,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    timeout: float | None = 300.0,
) -> subprocess.CompletedProcess[str] | None:
    """
    Run an external command safely.

    Hardening:

    - ``shell=False`` always (caller passes argv as a list).
    - Captures both streams as text.
    - Honours ``dry_run``: logs the command and returns ``None``
      without executing.
    - 5-minute default timeout.

    @param  argv     command + args.
    @param  dry_run  if True, log + skip.
    @param  cwd      working directory.
    @param  env      env vars to set (overlay; not full replace).
    @param  check    raise on non-zero exit.
    @param  timeout  seconds; ``None`` disables.
    @return CompletedProcess on apply; None on dry-run.
    @throws ReleaseKitError  on timeout or non-zero exit (when check=True).
    """
    if not argv:
        raise ValueError("argv cannot be empty")
    _log.info(
        "run-command",
        argv=argv,
        cwd=cwd,
        dry_run=dry_run,
        cmd_str=" ".join(shlex.quote(a) for a in argv),
    )
    if dry_run:
        return None

    full_env = None
    if env is not None:
        import os
        full_env = {**os.environ, **env}

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=full_env,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ReleaseKitError(
            f"command timed out after {timeout}s: {argv[0]}",
            code="subprocess-timeout",
            remediation="Increase timeout= or investigate the hang.",
        ) from e

    if check and result.returncode != 0:
        raise ReleaseKitError(
            f"command failed (exit {result.returncode}): {argv[0]}\n"
            f"stderr: {result.stderr.strip()}",
            code="subprocess-failed",
            remediation=None,
        )
    return result
