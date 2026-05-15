"""Multi-target publish workflow.

Composes the per-target lifecycle (authenticate -> validate ->
publish -> verify) across every enabled target. Honours
``policies.continue_on_error``; aborts on the first failure
otherwise.

This is the building block behind ``release-kit publish``. The CLI
file already inlines an equivalent flow; this module gives library
users a clean entry point.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..core.config import Config
from ..core.errors import ReleaseKitError
from ..core.logging import get_logger
from ..core.runner import RunContext, RunReport, StepOutcome
from ..platforms.base import Platform, load_platform_classes

_log = get_logger(__name__)


def run_publish(
    config: Config,
    *,
    selected: Iterable[str] | None = None,
    apply: bool = False,
) -> RunReport:
    """
    Execute the publish flow across selected targets.

    @param  config    loaded Config.
    @param  selected  target slugs to include. ``None`` = every enabled target.
    @param  apply     False = dry-run; True = real execution.
    @return RunReport
    """
    classes = load_platform_classes()
    pick = list(selected) if selected is not None else list(config.enabled_targets().keys())

    report = RunReport()
    for name in pick:
        tgt = config.targets.get(name)
        if tgt is None:
            outcome = StepOutcome(
                step="resolve",
                status="failed",
                detail=f"unknown target: {name}",
            )
            report.target_outcomes[name] = [outcome]
            report.failures.append(outcome)
            if not config.policies.continue_on_error:
                break
            continue
        if not tgt.enabled:
            continue
        cls = classes.get(name)
        if cls is None:
            outcome = StepOutcome(
                step="resolve",
                status="failed",
                detail=f"no plugin registered for {name!r}",
            )
            report.target_outcomes[name] = [outcome]
            report.failures.append(outcome)
            if not config.policies.continue_on_error:
                break
            continue

        plat = _instantiate(cls, tgt)
        ctx = RunContext(
            dry_run=not apply,
            policies=config.policies,
            target_name=name,
        )
        outcomes: list[StepOutcome] = []
        for step_fn in (plat.authenticate, plat.validate, plat.publish, plat.verify):
            try:
                outcome = step_fn(ctx)
            except ReleaseKitError as e:
                outcome = StepOutcome(
                    step=step_fn.__name__,
                    status="failed",
                    detail=str(e).splitlines()[0],
                    error=e,
                )
                outcomes.append(outcome)
                report.failures.append(outcome)
                if not config.policies.continue_on_error:
                    break
                continue
            outcomes.append(outcome)
            if outcome.status == "failed":
                report.failures.append(outcome)
                if not config.policies.continue_on_error:
                    break
        report.target_outcomes[name] = outcomes

    return report


def _instantiate(cls: type[Platform], target: object) -> Platform:
    """Build a platform instance, calling __post_init__ if present."""
    inst = cls.from_target(target)  # type: ignore[arg-type]
    post = getattr(inst, "__post_init__", None)
    if callable(post):
        post()
    return inst
