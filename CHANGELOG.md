# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No changes yet._

## [0.1.0] — 2026-05-15

### Added

- Project scaffold: pyproject.toml + hatchling build, Typer CLI,
  pydantic v2 config models, JSON Schema (draft 2020-12).
- Reference playbook at `docs/playbook/`: 33 markdown files covering
  26 platforms (17 registries + 9 git hosts) plus 6 cross-cutting
  topics. Identical 8-section template per platform.
- Core abstractions: `Platform`, `Registry`, `GitHost` ABCs with
  `AutomationLevel` and `AuthMethod` enums.
- Entry-point plugin registry: third parties add platforms via
  `[project.entry-points."release_kit.platforms"]`.
- Shared mixins: `DockerPushMixin`, `NpmPublishMixin`,
  `GitHubApiMixin`, `GitLabApiMixin`.
- 25 platform plugins registered:
  - **Registries (16)**: pypi, npm, npm-github, npm-gitlab,
    dockerhub, ghcr, gitlab-registry, aws-ecr, gar, acr, homebrew,
    rubygems, cargo, nuget, packagist, maven-central.
  - **Git hosts (8 + 1 inherited)**: github,
    github-enterprise-cloud, github-enterprise-server, gitlab,
    gitlab-self-managed, bitbucket, bitbucket-dc, gitea,
    azure-devops.
- CLI verbs: `init`, `doctor`, `publish`, `verify`,
  `bootstrap-repo`, `rotate-tokens`, `version`.
- Workflow composition modules (`workflows/`): `run_publish`,
  `run_bootstrap`, `apply_rotation` — usable independently of the
  CLI.
- Token resolution chain: override → env var → generic
  `RELEASE_KIT_TOKEN_<KEY>` → OS keyring. Audit logs the **source**,
  never the value; `redact_token` for any necessary previews.
- Subprocess hardening via `core.runner.run_command`:
  `shell=False`, 5-minute default timeout, argv-list-only.
- Dry-run by default; `--apply` required for any mutation.
- 158 tests, 76% line coverage (gate 70%); `ruff` + `mypy --strict`
  clean across 47 source files.
- Documentation: architecture, configuration, CLI, security,
  troubleshooting, plus 4 recipes and 4 workflow how-tos.
- `.github/` scaffolding: CI matrix on Linux + macOS + Windows ×
  Python 3.11 / 3.12 / 3.13 (ruff + mypy + pytest); tag-driven
  release workflow with OIDC trusted publishing to PyPI;
  Dependabot weekly on Monday 06:00 America/New_York; bug-report,
  feature-request, and config issue templates; PR template.
- 14 ADRs recording pre-flight decisions in `docs/decisions.md`.
- `VALIDATION.md` snapshot of v0.1.0 deliverables, gates run, and
  v0.2-deferred work.

### Deferred to v0.2

- Branch protection + environment / required-reviewer flows in
  `bootstrap-repo`.
- HEAD-probe in `doctor` validate step (today validates local
  config only).
- Provenance / SBOM as a first-class config block.
- conda-forge feedstock automation.
- Parallel-publish across targets.

[Unreleased]: https://github.com/simtabi/release-kit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/simtabi/release-kit/releases/tag/v0.1.0
