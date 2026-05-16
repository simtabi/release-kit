# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No changes yet._

## [0.2.0] — 2026-05-16

### Added

- **`release-kit verify`** verb (`f0daa28`): runs each target's
  `verify()` step in isolation. Useful as a periodic liveness check
  after publish.
- **HEAD-probe in `doctor`** (`68cb02e`): new `Platform.reach_probe()`
  method; PyPI override HEADs `https://pypi.org/simple/` with a 5s
  timeout. Doctor escalates GREEN → RED when reach fails.
- **Branch protection in `bootstrap-repo`** (`0cc6cd9`):
  declarative `branch_protection` block in TargetConfig passes through
  to GitHub's `PUT /repos/{repo}/branches/{branch}/protection`. Topics
  + branch protection now both ship under one verb.
- **Provenance / SBOM block** (`ec6dbdc`): new `PolicyConfig.provenance`
  with `require_sbom`, `sbom_path`, `attach_to_github_release`. Publish
  refuses to start when SBOM is required but missing.
- **Parallel publish** (`ff18d0e`): `policies.parallel_publish=true`
  runs target lifecycles concurrently via `ThreadPoolExecutor` sized
  by `policies.max_workers` (1..32, default 4).

### Changed

- CodeQL workflow (`311797c`): weekly + push/PR scan, python + actions
  languages, security-and-quality query set.
- README badges (`311797c`): CI status, PyPI version, supported
  Pythons, license.
- All four Node.js 20-deprecated actions bumped past the 2026-06-02
  cutoff (`3f4227a`): `checkout v4→v6`, `setup-python v5→v6`,
  `upload-artifact v4→v7`, `download-artifact v4→v8`.
- Repository security toggles enabled: secret-scanning,
  push-protection, dependabot-security-updates, private vulnerability
  reporting.

### Fixed

- `jsonschema>=4.21` added to `[dev]` extras (`44dc12a`): the bundled
  schema test was passing locally only because of an unrelated
  dependency.

### Deferred

- Environment / required-reviewer flows in `bootstrap-repo`.
- conda-forge feedstock automation (manual flow remains documented).
- SBOM generation (delegated to `cyclonedx-py` / `syft` by design).

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

[Unreleased]: https://github.com/simtabi/release-kit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/simtabi/release-kit/releases/tag/v0.2.0
[0.1.0]: https://github.com/simtabi/release-kit/releases/tag/v0.1.0
