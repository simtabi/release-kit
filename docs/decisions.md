# Architecture decisions

ADRs from the Phase 1 discovery, one heading per decision. Each
records the question, the resolved answer, the rationale, and any
alternatives considered.

## ADR-001: Path layout

**Status**: accepted (2026-05-15)

The package lives at
`/Users/imanimanyara/Artisan/projects/opensource/simtabi/python/release-kit/`,
matching the sibling pattern of other Python projects under
`simtabi/python/` (`downloader`, `python-laravel`, `resume-toolkit`).
The repository is independent (its own `.git`), not a sub-tree of any
parent.

## ADR-002: PyPI name

**Status**: accepted

PyPI distribution name: `simtabi-release-kit`. The `simtabi-` prefix
namespaces the package under the Simtabi organisation. The package
itself is generic; nothing in the runtime behaviour is tied to Simtabi
URLs, orgs, or projects. Every URL, namespace, and credential is
config-driven.

## ADR-003: Python floor

**Status**: accepted

Minimum Python: **3.11**. This diverges from sibling Simtabi packages
(`ai-configurator`, `get-installer`) which target 3.10. The bump is
justified by:

- `tomllib` in stdlib (3.11+) — read `pyproject.toml` without a
  runtime dep.
- `Self` type and structural pattern matching usable without compat
  shims.
- `ExceptionGroup` / `BaseExceptionGroup` for fan-out errors when
  publishing to multiple targets in parallel.

3.13 in CI matrix top; 3.11 and 3.12 also tested.

## ADR-004: CLI framework

**Status**: accepted

Typer. Pulls in Click and Rich. Chosen over argparse for ergonomics
(type-hint-driven option parsing) and over Click for the slightly
cleaner integration with Pydantic dataclasses.

## ADR-005: Build / dependency tool

**Status**: accepted

`uv` for local dev (venv + install + lock), `hatchling` as the
build backend declared in `pyproject.toml`. `pip` users are
supported through the same `pyproject.toml`; nothing in the package
requires `uv` to install.

## ADR-006: License

**Status**: accepted

MIT. Matches every other Simtabi OSS project.

## ADR-007: Runtime dependencies allowed

**Status**: accepted

Yes. Unlike sibling stdlib-only packages, release-kit needs a real
runtime dep footprint:

- `typer` (CLI)
- `pydantic>=2` (config validation)
- `structlog` (structured logging)
- `httpx` (HTTP client; `respx` for tests)
- `keyring` (OS credential store fallback)
- per-platform SDK clients as optional extras (e.g.,
  `boto3` only when `pip install simtabi-release-kit[aws]`)

All deps pinned with lower bounds + upper-bound discipline reviewed
annually. Optional extras keep the base install small.

## ADR-008: v0.1 platform scope

**Status**: accepted

All platforms enumerated below are coded in v0.1 (not stubbed).
Conda-forge is playbook-only because its workflow is PR-against
`staged-recipes` with heavy human review — "automation by default"
would be misleading.

**Registries (16)**: pypi · npm · npm-github · npm-gitlab · dockerhub
· ghcr · gitlab-registry · aws-ecr · gar · acr · homebrew ·
maven-central · rubygems · cargo · nuget · packagist

**Git hosts (9)**: github · github-enterprise-cloud ·
github-enterprise-server · gitlab · gitlab-self-managed · bitbucket
· bitbucket-dc · gitea · azure-devops

Each declares an `AutomationLevel` (FULL_API, OIDC_API, CLI_LOGIN,
PR_BASED, MANUAL_ONLY) so the runner and `doctor` command can reason
about which targets need human steps.

## ADR-009: Automation level is a first-class field

**Status**: accepted

Every `Platform` subclass declares `automation_level` and
`supported_auth_methods`. The CLI's `doctor` command renders a
colour-coded table. `publish --apply` refuses to run silently on
anything below `OIDC_API` / `FULL_API` — the user must acknowledge
PR-based or CLI-login targets explicitly. This avoids surprise
opens-a-PR-on-your-tap behaviour.

## ADR-010: GitHub repository naming

**Status**: accepted

`simtabi/release-kit` on GitHub (matches the local dir name). The
PyPI name `simtabi-release-kit` is the namespaced form; the repo
name is the short form for path consistency. Same pattern as
`simtabi/get-installer` (local + repo both `get-installer`).

## ADR-011: No simtabi-specific defaults anywhere in code

**Status**: accepted

The package name carries the Simtabi prefix; nothing else does.
Every example, default, and config path uses placeholder values
(`my-project`, `your-org`). The only Simtabi-tied surfaces are:

- The `simtabi-release-kit` distribution name on PyPI
- The `SECURITY.md` disclosure email (`opensource@simtabi.com`)
- The footer "Built by Simtabi LLC" attribution in README

End users of the package never need to touch any of those.

## ADR-012: Pluggable platform registry

**Status**: accepted

Third parties can add custom or private platforms without forking
release-kit. `pyproject.toml` exposes
`[project.entry-points."release_kit.platforms"]`; the core discovers
implementations at startup. Documented in
`docs/architecture.md::Extension points`.

## ADR-013: Dry-run by default on destructive operations

**Status**: accepted

`publish`, `bootstrap-repo`, and `rotate-tokens` default to dry-run.
Mutation requires `--apply` on the CLI or `.apply()` in the fluent
API. The CHANGELOG of every published release documents which
operations are reversible (almost none) so users plan accordingly.

## ADR-014: Coexisting `claude-configs/` directory

**Status**: investigated; no action

An empty `claude-configs/` directory exists alongside the
canonical `ai-configurator/` under `simtabi/`. The empty one is a
20 KB shell containing only `.claude/` and `.DS_Store`; it has no
`.git`. Almost certainly recreated by macOS Finder or an IDE
bookmark after the original `claude-configs → ai-configurator`
rename. Safe to ignore. Not deleted because the destructive-action
rule requires explicit user verb; user said "investigate", not
"delete".
