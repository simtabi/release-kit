"""Multi-target publish workflow.

Composes the per-target lifecycle (authenticate -> validate ->
publish -> verify) across every enabled target. Honours
``policies.continue_on_error``; aborts on the first failure
otherwise.

When ``policies.parallel_publish`` is True, targets run in a
``ThreadPoolExecutor`` sized by ``policies.max_workers`` (default
4). Steps within a single target stay sequential; only the
target-level loop parallelises. This is the building block behind
``release-kit publish``.
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait

from ..core.config import Config, TargetConfig
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

    # Provenance pre-flight: enforce SBOM presence before any target
    # gets to do work. A single up-front check beats discovering the
    # missing file mid-flight on target #5.
    prov = config.policies.provenance
    if prov is not None and prov.require_sbom:
        from pathlib import Path
        sbom = Path(prov.sbom_path)
        if not sbom.is_file():
            outcome = StepOutcome(
                step="provenance",
                status="failed",
                detail=(
                    f"SBOM not found at {sbom} (policies.provenance.require_sbom=true); "
                    f"generate with cyclonedx-py or syft and re-run"
                ),
            )
            report = RunReport()
            report.target_outcomes["<provenance>"] = [outcome]
            report.failures.append(outcome)
            return report

    if config.policies.parallel_publish:
        return _run_parallel(config, pick, classes, apply=apply)

    report = RunReport()
    for name in pick:
        outcomes, fatal = _run_one_target(config, name, classes, apply=apply)
        if outcomes is None:
            continue  # disabled target — silently skipped
        report.target_outcomes[name] = outcomes
        report.failures.extend([s for s in outcomes if s.status == "failed"])
        if fatal and not config.policies.continue_on_error:
            break

    return report


def _run_parallel(
    config: Config,
    pick: list[str],
    classes: dict[str, type[Platform]],
    *,
    apply: bool,
) -> RunReport:
    """Run each target's lifecycle in its own thread.

    `continue_on_error=False` cancels pending futures on first failure
    (best-effort: already-running targets finish their current step).
    """
    report = RunReport()
    workers = min(config.policies.max_workers, max(1, len(pick)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_run_one_target, config, name, classes, apply=apply): name
            for name in pick
        }
        if config.policies.continue_on_error:
            for fut in futures:
                name = futures[fut]
                outcomes, _ = fut.result()
                if outcomes is None:
                    continue
                report.target_outcomes[name] = outcomes
                report.failures.extend([s for s in outcomes if s.status == "failed"])
        else:
            done, pending = wait(futures.keys(), return_when=FIRST_EXCEPTION)
            for fut in done:
                name = futures[fut]
                outcomes, _ = fut.result()
                if outcomes is None:
                    continue
                report.target_outcomes[name] = outcomes
                report.failures.extend([s for s in outcomes if s.status == "failed"])
            # Cancel anything still queued. Already-running futures
            # complete and their results are dropped to keep the report
            # deterministic (only the first wave's results land).
            for fut in pending:
                fut.cancel()
    return report


def _run_one_target(
    config: Config,
    name: str,
    classes: dict[str, type[Platform]],
    *,
    apply: bool,
) -> tuple[list[StepOutcome] | None, bool]:
    """Execute one target's lifecycle. Returns (outcomes, fatal).

    `outcomes=None` when the target is disabled (silently skipped).
    `fatal=True` when a step failed AND `continue_on_error` is False
    (the caller should break/cancel).
    """
    tgt: TargetConfig | None = config.targets.get(name)
    if tgt is None:
        return [
            StepOutcome(
                step="resolve",
                status="failed",
                detail=f"unknown target: {name}",
            )
        ], True
    if not tgt.enabled:
        return None, False
    cls = classes.get(name)
    if cls is None:
        return [
            StepOutcome(
                step="resolve",
                status="failed",
                detail=f"no plugin registered for {name!r}",
            )
        ], True

    plat = _instantiate(cls, tgt)
    ctx = RunContext(
        dry_run=not apply,
        policies=config.policies,
        target_name=name,
    )
    outcomes: list[StepOutcome] = []
    fatal = False
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
            fatal = True
            if not config.policies.continue_on_error:
                break
            continue
        outcomes.append(outcome)
        if outcome.status == "failed":
            fatal = True
            if not config.policies.continue_on_error:
                break
    return outcomes, fatal


def _instantiate(cls: type[Platform], target: object) -> Platform:
    """Build a platform instance, calling __post_init__ if present."""
    inst = cls.from_target(target)  # type: ignore[arg-type]
    post = getattr(inst, "__post_init__", None)
    if callable(post):
        post()
    return inst
