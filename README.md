# simtabi-release-kit

[![CI](https://github.com/simtabi/release-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/simtabi/release-kit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/simtabi-release-kit.svg)](https://pypi.org/project/simtabi-release-kit/)
[![Python](https://img.shields.io/pypi/pyversions/simtabi-release-kit.svg)](https://pypi.org/project/simtabi-release-kit/)
[![License](https://img.shields.io/github/license/simtabi/release-kit.svg)](LICENSE)

Multi-registry publishing automation. One config file, one command,
every registry your project needs.

```bash
pip install simtabi-release-kit
release-kit init
release-kit doctor            # green / amber / red per target
release-kit publish --apply   # dry-run is the default
```

## What it does

- Publishes to **package registries**: PyPI, npm (+ GitHub Packages,
  GitLab npm), Docker Hub, GHCR, GitLab Container Registry, AWS
  ECR, Google Artifact Registry, Azure Container Registry, Homebrew
  tap, Maven Central, RubyGems, crates.io, NuGet, Packagist.
- Automates **git hosts**: GitHub.com, GitHub Enterprise (Cloud +
  Server), GitLab.com, GitLab Self-Managed, Bitbucket Cloud,
  Bitbucket Data Center, Gitea / Forgejo, Azure DevOps.
- **OIDC-first**: prefers passwordless trusted publishing.
  Refuses to fall back to long-lived tokens without
  `--allow-token-auth`.
- **Dry-run by default**: nothing publishes until `--apply`.
- **Pluggable**: third parties register custom platforms via
  `[project.entry-points."release_kit.platforms"]` without
  forking.

## Quick start

```bash
# 1. Install
pip install simtabi-release-kit

# 2. Scaffold a config + .env template
release-kit init

# 3. Verify your credentials and connectivity
release-kit doctor

# 4. Dry-run a publish to selected targets
release-kit publish --target pypi --target ghcr

# 5. For real
release-kit publish --target pypi --target ghcr --apply
```

## Two artefacts in one repo

This repository ships:

1. **A reference playbook** at [`docs/playbook/`](docs/playbook/) —
   33 markdown files covering every supported registry and git host,
   following an identical 8-section template. Read it standalone
   even if you never install the package.
2. **The Python automation package** under `src/release_kit/` —
   Typer CLI + config-driven runner + per-platform implementations.

## Status

| | |
|---|---|
| Version | 0.1.0 |
| Python | ≥ 3.11 |
| Platforms (playbook) | 26 platforms documented |
| Platforms (code) | 25 platforms registered (16 registries + 8 git hosts + 1 sub-class via inheritance) |
| Tests | 158 passing, 76% coverage (gate 70%) |
| Type-check | `mypy --strict` clean on 47 source files |

## Configuration

Three layers, highest wins:

1. CLI flags (`--target pypi --apply`)
2. Environment variables (loaded from `.env` in dev; from CI secret
   store in prod)
3. JSON config (`release.json`, validated against the bundled
   schema)

Example `release.json`:

```json
{
  "$schema": "./schema/release-kit.schema.json",
  "project": {
    "name": "my-project",
    "version_source": "pyproject.toml"
  },
  "targets": {
    "pypi":           { "enabled": true, "auth": "oidc" },
    "ghcr":           { "enabled": true, "auth": "oidc", "image": "ghcr.io/my-org/my-project" },
    "github_release": { "enabled": true, "draft": false, "generate_notes": true }
  },
  "policies": {
    "require_clean_git": true,
    "require_tag_match": true,
    "continue_on_error": false,
    "default_dry_run": true
  }
}
```

Full schema: [`docs/configuration.md`](docs/configuration.md).
JSON Schema (machine-readable): `src/release_kit/schema/release-kit.schema.json`.

## CLI surface

| Command | Purpose |
|---|---|
| `release-kit init` | Scaffold `release.json` + `.env-example` in the current dir |
| `release-kit doctor` | Per-target readiness check (green / amber / red) |
| `release-kit publish [--target NAME ...] [--apply]` | Run the publish flow |
| `release-kit bootstrap-repo [--apply]` | Apply topics (+ branch protection in v0.2) per config |
| `release-kit verify [--target NAME ...]` | Run each target's verify step to confirm artifacts are live |
| `release-kit rotate-tokens [--platform SLUG ...] [--list]` | Interactive token rotation helper |
| `release-kit version` | Print version |

Full reference: [`docs/cli.md`](docs/cli.md).

## Documentation

| | |
|---|---|
| [`docs/playbook/`](docs/playbook/) | The standalone reference for every supported platform |
| [`docs/architecture.md`](docs/architecture.md) | How the package is laid out + extension points |
| [`docs/configuration.md`](docs/configuration.md) | Full JSON config schema |
| [`docs/cli.md`](docs/cli.md) | Every command, every flag |
| [`docs/security.md`](docs/security.md) | Token handling, OIDC, rotation cadence |
| [`docs/workflows/`](docs/workflows/) | End-to-end how-tos (first publish, CI release, OIDC bootstrap) |
| [`docs/recipes/`](docs/recipes/) | Copy-pasteable example configs |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Symptom → cause → fix |

## Built by

[Simtabi LLC](https://simtabi.com) · MIT license · contributions welcome.
