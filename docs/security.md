# Security

How release-kit handles credentials, what it logs, and what it
will refuse to do.

## OIDC first

When a target supports OIDC trusted publishing (PyPI, npm, GHCR,
RubyGems, AWS ECR via GitHub-OIDC), that's the default. No
long-lived secrets touch the runner.

Set `policies.allow_token_auth = false` (the default) to **refuse**
silent fallback to a token. Operators must pass `--allow-token-auth`
on the CLI when a token-based publish is intentional.

## Token resolution chain

Order (highest precedence first):

1. CLI `--token <value>` (where the verb supports it).
2. `os.environ[<env_var>]` — primary env var per platform
   (`PYPI_TOKEN`, `NPM_TOKEN`, `GITHUB_TOKEN`, …).
3. `os.environ["RELEASE_KIT_TOKEN_<KEY>"]` — generic fallback, with
   `<KEY>` = slug.upper().replace("-", "_").
4. OS keyring under service `release-kit`, account `<slug>`.

If nothing resolves, the platform raises `AuthenticationError` with
code `token-not-found` and a remediation hint naming the env var.

## What is logged

Always: the **source** that resolved a token (`env:PYPI_TOKEN`,
`keyring:release-kit:pypi`, `override`). Never the value.

When a value must appear in logs (e.g. structured event for a
keyring write), `redact_token(value)` emits a prefix-only preview:
the first 4 characters + `…` + the length. Test with
`release_kit.core.logging.redact_token` if you're adding new log
sites.

## `.env` discovery

`load_env_file(path)` (or `--env-file`) takes precedence; otherwise
the standard python-dotenv search applies (`./.env`, ascending
parent directories until a `pyproject.toml`-style marker).

**`.env` must be gitignored.** `release-kit init` enforces this by
appending `.env` to the repo's `.gitignore` when scaffolding.

## Keyring

OS keyring is preferred for long-lived local tokens (macOS Keychain,
GNOME / KDE secret service, Windows Credential Manager). On
headless Linux without a backend, the library returns `None`
silently and falls back to env vars / `.env`.

Manage keyring entries with `release-kit rotate-tokens`. Direct CLI:

```python
from release_kit.core.secrets import set_keyring, delete_keyring
set_keyring("pypi", "pypi-AgEI-…")
delete_keyring("pypi")
```

## Subprocess hardening

Every external command runs through `core.runner.run_command`:

- `shell=False`; callers pass argv as a list.
- 5-minute default timeout (configurable).
- Both streams captured as text; non-zero exit becomes a typed
  `ReleaseKitError`.
- Timeouts become `code="subprocess-timeout"`.

No command-string concatenation, no shell metacharacters, no
implicit `$IFS` parsing.

## Refused operations

release-kit will refuse to:

- Publish from a dirty working tree (`policies.require_clean_git`).
- Publish when the local tag doesn't match the version source
  (`policies.require_tag_match`).
- Publish without a dated `CHANGELOG.md` entry for the version
  (`policies.require_changelog`).
- Fall back from OIDC to token without `--allow-token-auth`
  (`policies.allow_token_auth`).
- Run any `publish` step in dry-run mode against the real registry.

Each refusal carries an actionable `remediation` string.

## Vulnerability disclosure

Report to `opensource@simtabi.com`. See [`SECURITY.md`](../SECURITY.md).

## Recommended token scopes

Always prefer the **narrowest** scope:

| Platform | Recommended |
|---|---|
| PyPI | Per-project token (not account-wide). |
| npm | Automation token (bypasses 2FA OTP) scoped to one package. |
| GitHub.com | Fine-grained PAT scoped to one repo, only the permissions you need. |
| Docker Hub | Per-namespace access token, R/W/Delete. |
| GHCR | Fine-grained PAT with `Packages: Read & write` only. |
| GitLab | Project / Group Access Token, not personal PAT. |
| RubyGems | Per-gem scope (landed 2023). |
| crates.io | Per-crate scope (landed 2023). |
| NuGet | Glob-pattern scope to limit blast radius. |

Rotate at least annually; immediately on suspected compromise.
