# Architecture

This page is for people who want to read or extend the package
internals. Treat it as the map; per-platform contracts live in
[`playbook/`](playbook/).

## Layout

```text
src/release_kit/
├── cli/              Typer entry points (one verb per @app.command)
├── core/
│   ├── config.py     Pydantic v2 models (Config, ProjectConfig,
│   │                 TargetConfig, PolicyConfig)
│   ├── env.py        .env loader (python-dotenv passthrough)
│   ├── errors.py     Typed exception hierarchy with .code and
│   │                 .remediation
│   ├── logging.py    structlog setup + redact_token helper
│   ├── runner.py     RunContext, RunReport, StepOutcome,
│   │                 run_command (shell=False, 300s timeout)
│   └── secrets.py    Token resolution chain + keyring helpers
├── platforms/
│   ├── base.py       Platform ABC + Registry / GitHost subclasses,
│   │                 AutomationLevel + AuthMethod enums,
│   │                 load_platform_classes (entry-point walker)
│   ├── mixins/       Shared behaviours: DockerPushMixin,
│   │                 NpmPublishMixin, GitHubApiMixin, GitLabApiMixin
│   ├── registries/   One module per registry plugin
│   └── git_hosts/    One module per git-host plugin
├── workflows/        Composition modules: publish, bootstrap_repo,
│                     rotate_tokens
├── schema/           Bundled JSON Schema (release-kit.schema.json)
│                     + .env-example template
└── __init__.py       Public API re-exports
```

## The Platform contract

Every platform is a dataclass that subclasses `Platform` (registry
side) or `GitHost` (git-host side). Each declares three class-level
attributes:

| Attribute | Type | Meaning |
|---|---|---|
| `slug` | `str` | Stable identifier; matches the config key + entry-point name |
| `automation_level` | `AutomationLevel` | OIDC_API / FULL_API / CLI_LOGIN / PR_BASED / MANUAL_ONLY |
| `supported_auth_methods` | `tuple[AuthMethod, ...]` | OIDC, TOKEN, BASIC, CLI, NONE |

…and implements four lifecycle methods that take a `RunContext` and
return a `StepOutcome`:

1. `authenticate(ctx)` — resolve credentials, prove the platform is
   reachable. Never mutates anything.
2. `validate(ctx)` — confirm the local artifact / config is
   internally consistent (file present, name conforms, version
   parsable). Never mutates anything.
3. `publish(ctx)` — perform the mutation. Honors `ctx.dry_run`:
   when true, return `status="dry-run"` and skip the real call.
4. `verify(ctx)` — confirm the artifact is live (GET the new tag's
   manifest, follow the release URL, etc.).

`rollback(ctx)` is optional; the default returns `status="skipped"`.

## Discovery via entry points

Plugins are discovered through Python's
`importlib.metadata.entry_points` group `release_kit.platforms`. Each
entry maps a slug to an import path:

```toml
[project.entry-points."release_kit.platforms"]
pypi      = "release_kit.platforms.registries.pypi:PyPI"
ghcr      = "release_kit.platforms.registries.ghcr:GHCR"
github    = "release_kit.platforms.git_hosts.github:GitHub"
```

Third parties drop this in their own `pyproject.toml` and ship a
class that inherits from `Platform` / `Registry` / `GitHost`.
`release-kit doctor` picks them up after `pip install`.

## RunContext + reports

`RunContext(dry_run, policies, target_name)` is passed by value into
every lifecycle method. Platforms must not mutate it.

`StepOutcome(step, status, detail, error?)` is the per-step record.
`RunReport` aggregates per-target `StepOutcome` lists keyed by
target name. `RunReport.summary()` renders a one-line tally for the
CLI.

## Subprocess hygiene

All external commands go through `core.runner.run_command(argv,
dry_run=..., timeout=...)`. Hardening:

- `shell=False` always (callers pass argv lists).
- 5-minute default timeout (`subprocess.TimeoutExpired` → typed
  `ReleaseKitError`).
- Both streams captured as text; non-zero exit becomes a typed error
  unless `check=False`.

## Secrets

`core.secrets.resolve_token(key, env_var=..., override=...)` walks
the resolution chain: override → env_var → `RELEASE_KIT_TOKEN_<KEY>`
→ OS keyring (service `release-kit`) → `None`. The chain never logs
the value; only the **source** that resolved.

`apply_rotation` (in `workflows.rotate_tokens`) writes new tokens
into the keyring; the CLI's `rotate-tokens` verb walks operators
through the rotation per platform.

## Composition modules

`workflows/publish.py`, `workflows/bootstrap_repo.py`, and
`workflows/rotate_tokens.py` are the library entry points behind
the matching CLI verbs. Embed them in custom scripts when the
default CLI ergonomics don't fit.

## Where to extend

| Need | Add it here |
|---|---|
| New registry / git host | `platforms/{registries,git_hosts}/<slug>.py` + entry-point row |
| New mixin (shared behaviour) | `platforms/mixins/` |
| New CLI verb | `cli/app.py` (Typer command) + matching workflow module |
| New config field | `core/config.py` (TargetConfig has `extra="allow"` for free-form keys) |
| New error class | `core/errors.py` (subclass `ReleaseKitError`) |

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full extension
walkthrough.
