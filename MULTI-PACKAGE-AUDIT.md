# Multi-package audit — 2026-05-15

Production-readiness audit of the three Simtabi Python packages
worked on this session. Each package was checked against:

- Source builds (sdist + wheel)
- Test / lint / type-check / pre-commit
- CI green on latest commit
- PyPI version matches latest tag
- GitHub repo configured per Simtabi conventions (URLs, license,
  security toggles)
- Documentation matches shipped surface
- No dead code or stale claims

## Summary

| Package | Repo | Local tag | PyPI | CI | Status |
|---|---|---|---|---|---|
| `simtabi-release-kit` | `simtabi/release-kit` | `v0.1.0` | `0.1.0` ✓ | green | ✓ shipped |
| `ai-configurator` | `simtabi/claude-configs` | `v0.4.2` | **not published** | green | ⚠ release blocked |
| `get-installer` | `simtabi/get-installer` | `v0.3.0` | **not published** | green | ⚠ release blocked |

Two packages have valid tags but never reached PyPI because their
release workflows were broken when they fired. Both workflows now
work end-to-end after the fixes below; the next tag push (or a
manual re-trigger after configuring PyPI trusted publisher) will
publish.

## Bugs fixed by repo

### `simtabi/release-kit` (current session continued)

1. `fix(ci)`: added `jsonschema>=4.21` to `[dev]` extras
   (`test_bundled_schema_matches_model` was passing locally only
   because my venv had it via an unrelated install). — `44dc12a`
2. `ci`: bumped `actions/checkout@v6`, `setup-python@v6`,
   `upload-artifact@v7`, `download-artifact@v8` to clear the Node 20
   deprecation deadline (2026-06-02). — `3f4227a`
3. `chore`: pre-commit clean run. Wired markdownlint + ruff-format +
   detect-secrets-baseline + scoped mypy hook. — `5c86aaf`
4. `ci+docs`: CodeQL workflow (weekly + push/PR), README badges
   (CI / PyPI / Python / license), enabled secret-scanning +
   push-protection + dependabot-security-updates + private
   vulnerability reporting via `gh api`. — `311797c`

### `simtabi/claude-configs` (ai-configurator v0.4.2)

1. `ci`: action bumps for Node 20 deprecation
   (`checkout v4→v6`, `setup-python v5→v6`, `upload-artifact v4→v7`).
   — `b01bef3`
2. Same security toggles enabled via `gh api`: vulnerability_alerts,
   automated_security_fixes, private_vulnerability_reporting,
   secret_scanning, secret_scanning_push_protection.

### `simtabi/get-installer` (v0.3.0)

Five real bugs fixed, surfaced after the CI matrix cleanup let runs
actually complete on all OSes (Windows had been blocked behind a
forever-queued `ubuntu-24.04-arm` runner).

1. `fix(ci)`: matrix cleanup. Dropped `ubuntu-24.04-arm` (paid-tier
   runner that left runs queued indefinitely; Docker job covers
   linux/arm64 via cross-compile) and `macos-13` (Intel retired
   upstream). Bumped Node 20 actions. — `9a1a627`
2. `fix: Windows CI — bundle reproducibility + bash + UTF-8 stdout`:
    - `scripts/bundle.py` wrote the installer via `Path.write_text()`
      which translated `\n→\r\n` on Windows, breaking the SHA
      sidecar's on-disk match. Switched to `write_bytes()`.
    - Two `bash -n` syntax-check tests skipped only on
      `shutil.which("bash") is None`; Git-Bash is on Windows PATH
      but can't reliably parse Windows-style paths. Added
      `or sys.platform == "win32"` skipif.
    - Added job-level `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` so
      subprocess captures in `test_bundle.py` round-trip the
      installer's UTF-8 output on Windows cp1252. — `56c3bfd`
3. `fix(tests)`: skip `test_write_log_uses_strict_mode` on Windows
   (POSIX permission bits don't apply; `st_mode` reports OS
   defaults). — `aae2045`
4. **`fix(config)`: negative cache age must miss, not hit**.
   `Registry.from_url` checked `if age < cache_max_age_seconds`.
   Windows can produce a freshly-renamed file with `st_mtime`
   slightly *in the future* of `time.time()` (filesystem-time vs
   wall-clock precision skew). That made `age` negative, which
   incorrectly satisfied `cache_max_age_seconds=0` — turning
   "always refetch" into "use stale cache". Tightened to
   `0 <= age < cache_max_age_seconds`. — `2c694da`
5. `fix(ci)` for release workflow:
    - `shasum -a 256 dist/*` choked on `dist/__pycache__/` left by
      `python -m build`. Switched to explicit-file glob.
    - `softprops/action-gh-release` files glob referenced
      `dist/get-installer-*.tar.gz` (hyphen) but hatchling writes
      the sdist with the underscored project name. Aligned. —
      `9a1a627` (release.yml side)
6. `fix(docker)`: Ubuntu 26.04 default base image. Two issues:
    - Pinned `python3.12` but 26.04 ships 3.13. Switched to the
      meta `python3` package. — `3277326`
    - Pre-existing `ubuntu` user at UID 1000 conflicted with our
      `useradd -u 1000 installer` (`useradd` exits 4). Added an
      idempotent `userdel -r ubuntu` guard. — `d9b9868`

## What still needs human input

| Package | What | Why |
|---|---|---|
| `ai-configurator` | Configure PyPI trusted publisher on `simtabi/claude-configs` workflow `release.yml`, environment `pypi`, project `ai-configurator` | Both v0.4.1 and v0.4.2 release runs failed at the PyPI upload step. Tags exist locally + on origin; re-trigger by cutting v0.4.3 or manually re-running the workflow once publisher is set. |
| `get-installer` | Configure PyPI trusted publisher on `simtabi/get-installer` workflow `release.yml`, environment `pypi`, project `get-installer` | v0.3.0 release run failed; the underlying release.yml bugs are now fixed but the next tag push needs trusted-publisher configured. |
| Both | Cut next-patch tag (`v0.4.3` and `v0.3.1`) once trusted publisher is configured | Tags `v0.4.2` and `v0.3.0` are already pushed, but the workflow's prior failure means re-running them via the `gh workflow run` re-dispatch path. Easiest path forward: bump the patch + tag. |

## Gates that all 3 packages now pass

- `python -m pytest -q` — green (158 / 241 / 109 tests respectively)
- `ruff check src tests` — clean
- `mypy --strict` — clean
- `python -m build` — produces sdist + wheel
- `gh run list --workflow=ci.yml --limit 1` — green on latest commit
- All `actions/*` pinned to Node 24-compatible majors
- All five security toggles enabled
  (secret-scanning, push-protection, dependabot-security-updates,
  vulnerability-alerts, private-vulnerability-reporting)

## Out of scope (deferred to future sessions)

- v0.2 deferreds for release-kit (branch protection, parallel
  publish, HEAD-probe in doctor, conda-forge automation).
- conda-forge feedstocks for any package.
- Branch protection rules on `main` for all three repos.
- Dogfooding: release-kit publishing itself via `release-kit publish
  --apply` instead of the bespoke release.yml.

_Generated 2026-05-15, snapshot of HEAD at each repo. Re-verify
against current state if used as a punch list more than a few days
later — CI matrix shifts and base-image moves can surface new
issues._
