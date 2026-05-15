"""Typer entrypoint.

Every CLI verb lives here. Heavy lifting goes to the core / platforms
modules; this file is a thin orchestration layer.

Commands:

- ``init``          scaffold release.json + .env-example in cwd
- ``doctor``        per-target readiness check (green / amber / red)
- ``publish``       run the publish flow (dry-run by default)
- ``bootstrap-repo``  apply topics + branch protection per config (v0.2)
- ``verify``        confirm an artifact is live on a target
- ``rotate-tokens`` interactive token rotation (v0.2)
- ``version``       print the package version
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..core.config import Config, TargetConfig
from ..core.env import load_env_file
from ..core.errors import ReleaseKitError
from ..core.logging import configure as configure_logging
from ..core.logging import get_logger
from ..core.runner import RunContext, RunReport, StepOutcome
from ..platforms.base import (
    Platform,
    load_platform_classes,
)

app = typer.Typer(
    name="release-kit",
    help="Multi-registry publishing automation.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)
_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------


CONFIG_OPT = Annotated[
    Path,
    typer.Option(
        "--config", "-c",
        help="Path to release.json (default: ./release.json).",
        exists=False,
    ),
]

ENV_FILE_OPT = Annotated[
    Path | None,
    typer.Option(
        "--env-file",
        help="Path to .env (default: search order; see docs).",
    ),
]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Print the package version."""
    console.print(f"simtabi-release-kit {__version__}")


@app.command()
def init(
    target_dir: Annotated[
        Path,
        typer.Option(
            "--dir",
            help="Directory to scaffold into (default: cwd).",
        ),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing release.json / .env-example."),
    ] = False,
) -> None:
    """
    Scaffold ``release.json`` + ``.env-example`` in the target dir.

    Idempotent unless ``--force`` is passed: refuses to overwrite
    existing files.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    release_path = target_dir / "release.json"
    env_example_path = target_dir / ".env-example"
    gitignore_path = target_dir / ".gitignore"

    wrote: list[str] = []
    skipped: list[str] = []

    if release_path.exists() and not force:
        skipped.append(str(release_path))
    else:
        release_path.write_text(
            json.dumps(Config.example(), indent=2) + "\n",
            encoding="utf-8",
        )
        wrote.append(str(release_path))

    # .env-example: copy the bundled one if not present.
    if env_example_path.exists() and not force:
        skipped.append(str(env_example_path))
    else:
        env_example_path.write_text(_bundled_env_example(), encoding="utf-8")
        wrote.append(str(env_example_path))

    # Ensure .env is gitignored.
    gi_lines = (
        gitignore_path.read_text(encoding="utf-8").splitlines()
        if gitignore_path.exists()
        else []
    )
    if ".env" not in gi_lines:
        gi_lines.append(".env")
        gitignore_path.write_text("\n".join(gi_lines) + "\n", encoding="utf-8")
        wrote.append(f"{gitignore_path} (added .env)")

    for p in wrote:
        console.print(f"[green]wrote[/green]  {p}")
    for p in skipped:
        console.print(f"[yellow]skip[/yellow]   {p} (use --force to overwrite)")


@app.command()
def doctor(
    config: CONFIG_OPT = Path("release.json"),
    env_file: ENV_FILE_OPT = None,
) -> None:
    """
    Readiness check: green / amber / red per target.

    Exits non-zero when any target is RED. AMBER is a warning only;
    AMBER targets can still publish.
    """
    configure_logging("INFO")
    load_env_file(env_file)
    try:
        cfg = Config.from_path(config)
    except ReleaseKitError as e:
        _emit_error(e)
        raise typer.Exit(2) from e

    classes = load_platform_classes()

    table = Table(title="release-kit doctor")
    table.add_column("target")
    table.add_column("class")
    table.add_column("automation")
    table.add_column("status")
    table.add_column("detail")

    any_red = False
    for name, tgt in cfg.targets.items():
        cls = classes.get(name)
        if cls is None:
            table.add_row(name, "(unknown)", "—", "[red]RED[/red]", f"no plugin registered for {name!r}")
            any_red = True
            continue
        if not tgt.enabled:
            table.add_row(
                name,
                cls.__name__,
                cls.automation_level.value,
                "[grey50]DISABLED[/grey50]",
                "config.targets.enabled = false",
            )
            continue

        plat = _instantiate(cls, tgt)
        ctx = RunContext(
            dry_run=True,
            policies=cfg.policies,
            target_name=name,
        )
        try:
            auth_out = plat.authenticate(ctx)
            val_out = plat.validate(ctx)
            detail = f"{auth_out.detail}; {val_out.detail}"
            status = "[green]GREEN[/green]"
        except ReleaseKitError as e:
            detail = str(e).splitlines()[0]
            status = (
                "[red]RED[/red]" if e.code in {"token-not-found", "no-dist"} else "[yellow]AMBER[/yellow]"
            )
            if "RED" in status:
                any_red = True

        table.add_row(name, cls.__name__, cls.automation_level.value, status, detail)

    console.print(table)
    if any_red:
        raise typer.Exit(1)


@app.command(name="bootstrap-repo")
def bootstrap_repo(
    config: CONFIG_OPT = Path("release.json"),
    env_file: ENV_FILE_OPT = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Apply repo settings. Default is dry-run."),
    ] = False,
) -> None:
    """
    Apply declarative repo settings (topics, etc.) per git-host target.

    Dry-run by default. v0.1 supports GitHub topics; other hosts emit
    a "skipped — not yet implemented" step so the report is uniform.
    """
    from ..workflows.bootstrap_repo import run_bootstrap

    configure_logging("INFO")
    load_env_file(env_file)
    try:
        cfg = Config.from_path(config)
    except ReleaseKitError as e:
        _emit_error(e)
        raise typer.Exit(2) from e

    report = run_bootstrap(cfg, apply=apply)
    _print_run_report(report, dry_run=not apply)
    if not report.ok:
        raise typer.Exit(1)


@app.command(name="rotate-tokens")
def rotate_tokens(
    platform: Annotated[
        list[str] | None,
        typer.Option(
            "--platform", "-p",
            help="Platform slug(s) to rotate (repeatable). Default: prompt for each.",
        ),
    ] = None,
    list_only: Annotated[
        bool,
        typer.Option("--list", help="Print the rotation table and exit."),
    ] = False,
) -> None:
    """
    Interactive token rotation.

    For each selected platform: prints the management URL, prompts for
    the new token (silent input), then stores it via the OS keyring.
    Never echoes the value.
    """
    from ..workflows.rotate_tokens import (
        ROTATION_TABLE,
        apply_rotation,
        get_rotation_step,
    )

    if list_only:
        table = Table(title="release-kit rotate-tokens")
        table.add_column("slug")
        table.add_column("platform")
        table.add_column("token URL")
        table.add_column("env var")
        for slug, step in ROTATION_TABLE.items():
            table.add_row(slug, step.platform, step.token_management_url, step.env_var)
        console.print(table)
        return

    selected = platform or list(ROTATION_TABLE.keys())
    for slug in selected:
        try:
            step = get_rotation_step(slug)
        except KeyError as e:
            err_console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        console.print(f"\n[bold]{step.platform}[/bold] ({slug})")
        console.print(f"  URL: {step.token_management_url}")
        if step.notes:
            console.print(f"  note: {step.notes}")
        new_value = typer.prompt(
            f"  new token for {slug} (input hidden, blank to skip)",
            default="",
            hide_input=True,
            show_default=False,
        )
        if not new_value:
            console.print("  [yellow]skipped[/yellow]")
            continue
        apply_rotation(slug, new_value)
        console.print(f"  [green]stored[/green] in OS keyring under release-kit:{slug}")


@app.command()
def publish(
    config: CONFIG_OPT = Path("release.json"),
    env_file: ENV_FILE_OPT = None,
    target: Annotated[
        list[str] | None,
        typer.Option("--target", help="Restrict to these targets. Repeatable."),
    ] = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Actually run the publish. Default is dry-run."),
    ] = False,
) -> None:
    """
    Run the publish flow.

    Default is dry-run: every step is logged + planned but no
    external mutation happens. Pass ``--apply`` to actually
    publish.
    """
    configure_logging("INFO")
    load_env_file(env_file)
    try:
        cfg = Config.from_path(config)
    except ReleaseKitError as e:
        _emit_error(e)
        raise typer.Exit(2) from e

    classes = load_platform_classes()
    selected = target or list(cfg.enabled_targets().keys())

    report = RunReport()
    for name in selected:
        tgt = cfg.targets.get(name)
        if tgt is None:
            err_console.print(f"[red]unknown target[/red]: {name}")
            raise typer.Exit(2)
        if not tgt.enabled:
            console.print(f"[yellow]disabled[/yellow]: {name}")
            continue
        cls = classes.get(name)
        if cls is None:
            err_console.print(f"[red]no plugin for target[/red]: {name}")
            raise typer.Exit(2)

        plat = _instantiate(cls, tgt)
        ctx = RunContext(
            dry_run=not apply,
            policies=cfg.policies,
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
                if not cfg.policies.continue_on_error:
                    break
                continue
            outcomes.append(outcome)
            if outcome.status == "failed":
                report.failures.append(outcome)
                if not cfg.policies.continue_on_error:
                    break
        report.target_outcomes[name] = outcomes

    _print_run_report(report, dry_run=not apply)
    if not report.ok:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _instantiate(cls: type[Platform], target: TargetConfig) -> Platform:
    """Construct a platform instance, calling __post_init__ if defined."""
    inst = cls.from_target(target)
    post = getattr(inst, "__post_init__", None)
    if callable(post):
        post()
    return inst


def _print_run_report(report: RunReport, *, dry_run: bool) -> None:
    """Pretty per-target outcomes."""
    table = Table(title="publish report" + (" (dry-run)" if dry_run else ""))
    table.add_column("target")
    table.add_column("step")
    table.add_column("status")
    table.add_column("detail")
    for name, steps in report.target_outcomes.items():
        for s in steps:
            colour = {
                "ok": "green",
                "dry-run": "cyan",
                "skipped": "grey50",
                "failed": "red",
            }.get(s.status, "white")
            table.add_row(name, s.step, f"[{colour}]{s.status.upper()}[/{colour}]", s.detail)
    console.print(table)
    console.print(report.summary())


def _emit_error(e: ReleaseKitError) -> None:
    err_console.print(f"[red]error[/red]: {e}")


def _bundled_env_example() -> str:
    """Read the bundled .env-example template that ships with the wheel."""
    # Walk up from this module to the package root and read the
    # template that lives at the repo root. When packaged, we copy
    # it into the resources tree (see pyproject.toml::tool.hatch.build).
    from importlib import resources
    try:
        ref = resources.files("release_kit") / "schema" / ".env-example"
        if ref.is_file():
            return ref.read_text(encoding="utf-8")
    except Exception:  # pragma: no cover
        pass
    # Fallback for editable installs: read from repo root.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env-example"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return "# release-kit .env template\n# (no bundled .env-example found)\n"


if __name__ == "__main__":
    app()
