# Security policy

## Supported versions

The `simtabi-release-kit` project supports the latest two minor
releases. Older releases receive critical-severity fixes only.

| Version | Status |
|---------|--------|
| 0.1.x | Current (supported) |

## Reporting a vulnerability

**Do not open a public GitHub issue for security problems.**

Disclosure goes to `opensource@simtabi.com`. Include:

- A description of the vulnerability and its impact.
- Steps to reproduce (minimum proof-of-concept).
- The version(s) you tested.
- Optionally: a suggested fix.

Expect a response within 5 business days.

## Scope

In scope:

- The `simtabi-release-kit` Python package on PyPI.
- The source in this repository.
- The CLI, the public `release_kit.*` API, the JSON schema.

Out of scope:

- Vulnerabilities in third-party clients (`twine`, `gh`, `docker`,
  cloud SDKs). Report to those projects' security teams.
- The customer's CI configuration, secret-store, or token rotation
  policy. Documented best practices in
  [`docs/security.md`](docs/security.md).
- Issues in the registries themselves (PyPI, npm, Docker Hub).

## Built-in protections

The package enforces these at runtime:

1. **Token resolution is auditable.** Source of each resolved
   token is logged (env name, keyring entry, `.env`); the **value**
   is never logged.
2. **OIDC preferred.** Refuses to fall back to long-lived tokens
   without `--allow-token-auth`.
3. **TLS verification on.** All HTTP calls use the default
   `httpx` config (verify=True).
4. **No `shell=True`.** Every subprocess invocation uses an
   argv list. No string-interpolation of user input.
5. **Dry-run by default.** External-facing operations require
   `--apply` to mutate.
6. **No secret patterns committed.** Detect-secrets pre-commit
   hook + a CI check refuse PRs that introduce token-shaped
   strings.

## Disclosure timeline

| Day | Step |
|---|---|
| 0   | Vulnerability reported via email. |
| ≤ 5 | Initial response + severity triage. |
| ≤ 14 | Fix in private branch + tests. |
| ≤ 30 | Coordinated public release with credit (if desired). |
| 31+ | CVE filed where applicable. |

We use [coordinated vulnerability disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure).
