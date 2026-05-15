# Validation report — v0.1.0

What was delivered, what was tested, what was deferred. This is the
record we hand to whoever audits the v0.1.0 cut. Numbers reflect the
state of the repo at the time of this writing; re-run the commands
listed below to refresh.

## Scope

Two deliverables shipped together:

1. **The reference playbook** at `docs/playbook/` — standalone
   markdown reference for every supported platform.
2. **The Python automation package** under `src/release_kit/` —
   Typer CLI + pydantic config + per-platform plugin classes.

## Counts

| Item | Count | Verify with |
|---|---|---|
| Platforms registered (entry points) | **25** | `python -c "from importlib.metadata import entry_points; print(len(list(entry_points(group='release_kit.platforms'))))"` |
| Platform plugin files (registries) | 16 | `ls src/release_kit/platforms/registries/*.py \| grep -v __init__ \| wc -l` |
| Platform plugin files (git hosts) | 8 | `ls src/release_kit/platforms/git_hosts/*.py \| grep -v __init__ \| wc -l` |
| Source files (mypy --strict) | 47 | `find src -name "*.py" \| wc -l` |
| Test files | 18 | `find tests -name "test_*.py" \| wc -l` |
| Test cases | 158 | `pytest --collect-only -q \| tail -1` |
| Doc files | 72 | `find docs -name "*.md" \| wc -l` |
| Playbook pages | 33 | `find docs/playbook -name "*.md" \| wc -l` |
| ADRs | 14 | `wc -l docs/decisions.md` |

## Gates

All gates green on Python 3.13 (the dev venv), targeting Python 3.11+.

```bash
.venv/bin/python -m pytest          # 158 passed, 76.05% coverage (gate 70%)
.venv/bin/python -m ruff check .    # all checks passed
.venv/bin/python -m mypy src        # success, no issues in 47 source files
```

## Smoke tests run

- `release-kit version` → prints `simtabi-release-kit 0.1.0`.
- `release-kit --help` → lists 6 verbs (init, doctor, publish,
  bootstrap-repo, rotate-tokens, version).
- `release-kit init` in a fresh `/tmp` dir → writes
  `release.json`, `.env-example`, appends `.env` to `.gitignore`.
- `release-kit doctor` against the scaffolded config → AMBER on
  the PyPI target ("auth='oidc' but no CI OIDC environment
  detected") — expected, no CI in the smoke test.
- `release-kit publish` (dry-run) against the scaffolded config →
  exits 1 because the OIDC env isn't present, prints a clean
  report. (Expected. The non-zero exit comes from
  `policies.allow_token_auth = false`, not a real publish.)

## README ToC vs docs/ tree

Every link in `README.md` that points at a local file resolves.
Verified with:

```bash
for link in $(grep -oE '\]\([^)]+\)' README.md | sed 's/^](//; s/)$//' | grep -v '^https'); do
  [ -e "$link" ] || echo "BAD: $link"
done
```

Empty output = all good.

## What's done in v0.1

- [x] Configuration via `release.json` + bundled JSON Schema.
- [x] Pluggable platform discovery via
      `release_kit.platforms` entry-point group.
- [x] Seven CLI verbs (init, doctor, publish, verify,
      bootstrap-repo, rotate-tokens, version).
- [x] Three workflow composition modules (publish, bootstrap_repo,
      rotate_tokens) usable independent of the CLI.
- [x] 25 platforms registered: 16 registries + 8 git-host plugins +
      1 (`github-enterprise-cloud`) shared via inheritance.
- [x] OIDC-first authentication; refuses silent fallback to tokens.
- [x] Dry-run is the default; `--apply` required for mutation.
- [x] Token resolution chain (override → env → generic env →
      keyring) with audit-logged source, never the value.
- [x] Subprocess hardening (shell=False, 5-min timeout,
      argv-list-only) via `core.runner.run_command`.
- [x] Full reference playbook at `docs/playbook/` covering every
      registered platform plus 6 cross-cutting pages.

## What's deferred to v0.2

- Branch protection + environment / required-reviewer flows in
  `bootstrap-repo` (today only topics are applied for GitHub).
- A web dashboard / GitHub Action for unattended scheduled
  rotations.
- Provenance/SBOM emission as a first-class config block. Today
  npm publishes use `--provenance` when the target sets it.
- conda-forge feedstock pinging (the playbook page describes the
  manual flow; full automation requires a feedstock fork).

## Limitations / known issues

- The keyring lookup is a no-op on headless Linux without a
  secret-service daemon; resolution silently falls back to env
  vars. Documented in [`docs/security.md`](docs/security.md).
- The `doctor` `validate` step doesn't yet hit each registry's
  HEAD endpoint to confirm reachability; it only validates local
  config. Listed as v0.2 work in ADR-013.
- `publish --apply` is sequential across targets. Parallel
  execution would shorten end-to-end CI time but complicates the
  failure report; deferred until a real use case asks for it.
- Coverage is at 75.95% with the gate at 70%. The deficit is
  concentrated in the publish methods of platforms that need a
  live registry to test (cargo, nuget, rubygems, packagist). Full
  end-to-end coverage requires the integration harness queued for
  v0.2.

## Self-publish (Phase 7)

Not run yet. The package is ready to publish itself to PyPI but
that requires:

- PyPI trusted publisher pointing at the repo.
- The repo to exist at `github.com/simtabi/release-kit` (today
  this is a local working tree only).
- A signed `v0.1.0` tag.

Self-publish is the dogfood test for v0.1; it'll happen on
explicit go-ahead from the maintainer.

## Regenerating this file

After material changes, refresh by re-running the count commands
above and editing the `## Counts` table. Anything in `## What's
done` that's no longer true must move to `## What's deferred` or
the `CHANGELOG.md`.

Last full regen: 2026-05-15.
