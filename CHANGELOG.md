# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project scaffold: pyproject.toml, hatchling build,
  Typer CLI, pydantic v2 config models, JSON Schema.
- Complete reference playbook: 33 markdown files covering 26
  platforms (17 registries + 9 git hosts) plus 6 cross-cutting
  topics. Template-compliant; ToC mirrors tree exactly.
- Core abstractions: `Platform`, `Registry`, `GitHost` ABCs with
  `AutomationLevel` and `AuthMethod` enums.
- Entry-point plugin registry: third parties add platforms via
  `[project.entry-points."release_kit.platforms"]`.
- PyPI fully implemented as the reference platform.
- Working CLI verbs: `init`, `doctor`, `publish`, `version`.
- Test suite + coverage gates (≥85% on `core/` + `platforms/base.py`,
  ≥70% overall).
- Pre-commit hooks: ruff, mypy, detect-secrets, end-of-file-fixer.
- `.github/` scaffolding: CI matrix on Linux + macOS + Windows ×
  Python 3.11 / 3.12 / 3.13; release workflow; Dependabot;
  CodeQL.
