# Troubleshooting

Symptom → cause → fix.

## "no plugin registered for `<slug>`"

**Cause**: The slug in `release.json` doesn't match a registered
entry-point.

**Fix**: Check `release-kit doctor`; look for typos. Confirm the
plugin's package is installed (`pip show simtabi-release-kit`).
For third-party plugins, confirm they've registered under the
`release_kit.platforms` entry-point group:

```bash
python -c "from importlib.metadata import entry_points; \
  print([ep.name for ep in entry_points(group='release_kit.platforms')])"
```

## "token-not-found"

**Cause**: The platform walked the resolution chain (env var →
generic fallback → keyring) and found nothing.

**Fix**: Set the platform's primary env var, e.g.:

```bash
export PYPI_TOKEN="pypi-AgEI..."
```

…or rotate via `release-kit rotate-tokens --platform pypi` to store
it in the OS keyring.

## `subprocess-timeout` on Docker push

**Cause**: 5-minute default timeout, large image push to a slow
network or a rate-limited registry.

**Fix**: Pre-pull the base layers and rebuild from local cache
before the publish run. Or call `run_command(..., timeout=900)`
when embedding the workflow yourself.

## "command failed (exit 1): docker login"

**Cause**: Stored credentials are stale or the registry endpoint
moved.

**Fix**: `docker logout <host>` then re-rotate:

```bash
release-kit rotate-tokens --platform dockerhub
```

## "config schema violation"

**Cause**: `release.json` fails pydantic validation.

**Fix**: The error message points at the offending field. Cross-
reference [`docs/configuration.md`](configuration.md) and the
bundled JSON Schema at
[`src/release_kit/schema/release-kit.schema.json`](../src/release_kit/schema/release-kit.schema.json).

## "GitHub API … returned 403"

**Cause**: Token lacks scope, or the repo enforces SSO without an
authorized PAT, or you hit the secondary rate limit.

**Fix**:

- Confirm the PAT has `Contents: Write` for releases, `Metadata:
  Read` for topics.
- If the org enforces SSO, click "Configure SSO" on the token in
  GitHub settings.
- Re-run after waiting 60 seconds for the secondary limit to clear.

## "GitHub API … returned 422 — already_exists"

**Cause**: The release tag already exists.

**Fix**: This is idempotent: `release-kit verify` will report
`status="ok"`. If you genuinely need to replace the release, delete
it via the GitHub UI first; release-kit refuses to destroy
published artifacts implicitly.

## "verify-not-found" on Docker Hub

**Cause**: The push completed, but the registry hasn't indexed the
tag yet.

**Fix**: Wait ~60 seconds; re-run `release-kit verify --target
dockerhub`. If still not found after a few minutes, check the
Docker Hub status page; if the registry is OK, the push silently
failed and the publish step's exit code lied — open an issue.

## OIDC ID-token request fails on CI

**Cause**: The workflow lacks `id-token: write` permission, or it's
not running on a GitHub-hosted runner / OIDC-aware provider.

**Fix**: Add to your workflow file:

```yaml
permissions:
  id-token: write
  contents: read
```

…or set `auth: "token"` and pass `--allow-token-auth` for that run.

## Doctor shows AMBER for every target

**Cause**: `validate()` is finding non-fatal issues (missing
optional fields, unset environment toggles).

**Fix**: AMBER targets can still publish. Read the `detail` column;
fix what matters, ignore the rest. AMBER is a hint, not a block.

## "no rotation guidance for `<slug>`"

**Cause**: The slug isn't in
`release_kit.workflows.rotate_tokens.ROTATION_TABLE`.

**Fix**: Open a PR adding a `RotationStep` entry for the new
platform, or rotate manually via the platform's own UI and store
via:

```python
from release_kit.core.secrets import set_keyring
set_keyring("<slug>", "<token>")
```

## Empty `docs/playbook/` link in README on a fresh clone

**Cause**: You're on the install-from-PyPI workflow; the playbook
ships only via the source tree, not the wheel.

**Fix**: `git clone https://github.com/simtabi/release-kit` and
read [`docs/playbook/`](playbook/) there.

## Still stuck

File at <https://github.com/simtabi/release-kit/issues> with:

- The `release-kit doctor` table output.
- Your `release.json` (redact tokens).
- The exact CLI command + stderr (re-run with `--log-level=DEBUG`
  if structlog is wired up).
