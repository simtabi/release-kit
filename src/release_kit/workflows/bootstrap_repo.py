"""Apply repo topics + branch protection per config.

Only meaningful for git-host targets (github, gitlab, etc.).
Walks the configured targets, asks each git-host plugin to apply
its declarative settings (topics, branch protection).

GitHub-flavoured hosts support `topics` (PUT /repos/{repo}/topics)
and `branch_protection` (PUT /repos/{repo}/branches/{branch}/protection).
Other hosts emit `skipped` for both.
"""

from __future__ import annotations

from ..core.config import Config
from ..core.errors import PlatformError
from ..core.logging import get_logger
from ..core.runner import RunContext, RunReport, StepOutcome
from ..platforms.base import GitHost, load_platform_classes
from ..platforms.git_hosts.github import GitHub

_log = get_logger(__name__)


def run_bootstrap(config: Config, *, apply: bool = False) -> RunReport:
    """
    Apply repo settings declared in each git-host target's config.

    Currently supports topics for any GitHub-flavoured host
    (github, GHEC, GHES via inheritance). Other git hosts get a
    "skipped — bootstrap not yet implemented" outcome so the report
    is uniform.

    @param  config  loaded Config.
    @param  apply   False = dry-run.
    @return RunReport
    """
    classes = load_platform_classes()
    report = RunReport()

    for name, tgt in config.targets.items():
        if not tgt.enabled:
            continue
        cls = classes.get(name)
        if cls is None or not issubclass(cls, GitHost):
            continue

        plat_obj = cls.from_target(tgt)
        post = getattr(plat_obj, "__post_init__", None)
        if callable(post):
            post()

        ctx = RunContext(
            dry_run=not apply,
            policies=config.policies,
            target_name=name,
        )

        outcomes: list[StepOutcome] = []

        # Auth probe
        try:
            outcomes.append(plat_obj.authenticate(ctx))
        except Exception as e:
            outcomes.append(StepOutcome("authenticate", "failed", str(e).splitlines()[0], error=e))
            report.target_outcomes[name] = outcomes
            report.failures.append(outcomes[-1])
            if not config.policies.continue_on_error:
                break
            continue

        # Topics + branch protection (GitHub flavours)
        if isinstance(plat_obj, GitHub):
            topics = plat_obj._topics
            if topics:
                if ctx.dry_run:
                    outcomes.append(
                        StepOutcome("topics", "dry-run", f"would set {len(topics)} topic(s)")
                    )
                else:
                    try:
                        plat_obj._api_put(
                            ctx,
                            f"/repos/{plat_obj._repo}/topics",
                            json={"names": topics},
                            env_var=plat_obj._env_var,
                        )
                        outcomes.append(
                            StepOutcome("topics", "ok", f"applied {len(topics)} topic(s)")
                        )
                    except PlatformError as e:
                        outcomes.append(StepOutcome("topics", "failed", str(e), error=e))
                        report.failures.append(outcomes[-1])

            bp = plat_obj._branch_protection
            if bp:
                bp_body = dict(bp)
                branch = str(bp_body.pop("branch", "main"))
                path = f"/repos/{plat_obj._repo}/branches/{branch}/protection"
                if ctx.dry_run:
                    outcomes.append(
                        StepOutcome(
                            "branch_protection",
                            "dry-run",
                            f"would PUT {path} ({len(bp_body)} setting(s))",
                        )
                    )
                else:
                    try:
                        plat_obj._api_put(
                            ctx, path, json=bp_body, env_var=plat_obj._env_var
                        )
                        outcomes.append(
                            StepOutcome(
                                "branch_protection",
                                "ok",
                                f"applied to {branch}",
                            )
                        )
                    except PlatformError as e:
                        outcomes.append(
                            StepOutcome("branch_protection", "failed", str(e), error=e)
                        )
                        report.failures.append(outcomes[-1])
        else:
            outcomes.append(
                StepOutcome("topics", "skipped", "bootstrap not yet implemented for this host")
            )

        report.target_outcomes[name] = outcomes

    return report
