# Contributing to simtabi-release-kit

## Read first

- [`README.md`](README.md) — what this package is, install, quickstart
- [`docs/architecture.md`](docs/architecture.md) — module boundaries
  and how a new platform plugs in
- [`docs/security.md`](docs/security.md) — token handling rules

## Development setup

```bash
# bash
git clone https://github.com/simtabi/release-kit
cd release-kit
uv venv && source .venv/bin/activate
uv pip install -e '.[dev,all]'
pre-commit install

make test
make lint
```

All four (pytest, ruff, mypy, pre-commit) must be green on every PR.
CI runs the same on Linux + macOS + Windows × Python 3.11 / 3.12 / 3.13.

## Architecture rules

1. **One class per platform.** New AI-agent target adds a class to
   `src/release_kit/platforms/registries/` or
   `src/release_kit/platforms/git_hosts/` and registers it in
   `pyproject.toml::[project.entry-points."release_kit.platforms"]`.
2. **No simtabi-specific defaults.** The package is generic.
   Every URL, namespace, env-var name is config-driven.
3. **Dry-run is the master safety.** Any operation that mutates an
   external service defaults to dry-run; `--apply` (or
   `apply=True` in the fluent API) is required to mutate.
4. **Token resolution chain**, in order: explicit param → env var →
   `.env` → OS keyring → fail. Never silently fall back from OIDC
   to a long-lived token without `--allow-token-auth`.
5. **No shell strings.** Every subprocess invocation uses
   `subprocess.run([...], shell=False)`. No `shell=True`. No
   string-interpolating user input.
6. **TLS verification on.** No `verify=False` anywhere.
7. **No global state.** Every config flows through explicit
   parameters; no module-level singletons.

## Coding conventions

- `mypy --strict` clean. Prefer `Self` over forward-string types.
- `ruff` clean with the selected ruleset.
- Tests live in `tests/` mirroring the source tree.
- Every public class + method has a Laravel-style docblock:
  ```python
  def publish(self, *, dry_run: bool = True) -> "PublishResult":
      """
      Publish the configured artifacts to all selected targets.

      Iterates each registered target, runs preflight, then executes
      the upload. Aborts on the first failure unless
      ``continue_on_error`` is set.

      @param  dry_run   When True, no network calls are made.
      @return PublishResult  Aggregated per-target outcome.
      @throws AuthenticationError  When credentials are invalid.
      """
  ```

## Commit messages

- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`).
- Imperative subject ≤ 72 chars.
- Body explains the **why**, not the **what**.
- No emoji, no `Co-Authored-By` trailers.
- AI-tells (`leverage`, `seamless`, `essentially`, `note that`,
  `simply,`, `comprehensive`, `robust`, `delve into`, `let's dive`)
  are blocked.

## Adding a new platform

1. Implement the class under `src/release_kit/platforms/registries/`
   or `git_hosts/`, subclassing `Registry` or `GitHost` (see
   `platforms/base.py`).
2. Set `automation_level` and `supported_auth_methods` as class
   attributes.
3. Register in `pyproject.toml`:
   ```toml
   [project.entry-points."release_kit.platforms"]
   my-platform = "release_kit.platforms.registries.my_platform:MyPlatform"
   ```
4. Add unit tests under `tests/platforms/registries/`.
5. Add the platform's playbook page under `docs/playbook/registries/`
   (template in `docs/playbook/README.md`).
6. Add a thin per-package doc at `docs/platforms/<name>.md` that
   links to the playbook.

## Reporting bugs

Issues at https://github.com/simtabi/release-kit/issues. Include:
- `release-kit --version`
- Python version + OS
- Minimum reproduction (config + command + output)

## Reporting security issues

See [`SECURITY.md`](SECURITY.md). Don't open a public issue.
