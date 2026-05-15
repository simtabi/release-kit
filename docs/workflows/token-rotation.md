# Token rotation

A scheduled cadence + an emergency drill.

## Cadence

- **At least annually** per platform.
- **Immediately on suspected compromise**: stolen laptop,
  committed-then-reverted `.env`, departed maintainer.
- **Quarterly** for high-impact secrets (PyPI, GHCR, Docker Hub).

The rotation table in
[`release_kit.workflows.rotate_tokens`](../../src/release_kit/workflows/rotate_tokens.py)
names each platform's URL + the env-var/keyring slot the runner
uses.

## Routine rotation

```bash
release-kit rotate-tokens --list           # show known platforms
release-kit rotate-tokens --platform pypi  # rotate one
release-kit rotate-tokens                  # walk every platform
```

For each platform:

1. The CLI prints the management URL — open it.
2. Create the new token in the registry/host UI.
3. Paste it at the prompt (input is hidden).
4. The new value is written to the OS keyring under
   service `release-kit`, account `<slug>`.
5. Old token: revoke it in the same UI before closing the tab.

Re-run `release-kit doctor` to confirm the new token resolves.

## Emergency drill

When you believe a token is leaked:

1. **Revoke first**, ask questions later. Use the platform UI's
   "revoke" / "delete" button on the suspected token. The platform
   refuses subsequent calls within seconds.
2. Create a replacement.
3. `release-kit rotate-tokens --platform <slug>` to store it.
4. Re-run any in-flight CI jobs that depended on the old token.
5. Audit the platform's audit log for unexpected pushes / pulls
   while the token was valid.
6. Post-mortem: how did it leak? Was it in a log, a `.env` checked
   into git history, a screenshot?

## CI tokens

Rotation in the OS keyring doesn't touch the CI secret store. Two
options:

- **OIDC-capable targets**: drop the long-lived token entirely
  ([`oidc-bootstrap.md`](oidc-bootstrap.md)).
- **Token-only targets**: rotate via the platform UI, then update
  the CI secret. GitHub: `Settings → Secrets and variables →
  Actions → <SECRET> → Update`.

## Verifying rotation

After a rotation:

```bash
unset PYPI_TOKEN              # ensure env doesn't shadow keyring
release-kit doctor            # target should show GREEN with auth from keyring
```

If GREEN: the keyring lookup found the new value.
If RED with `token-not-found`: the keyring write failed or the
slot name doesn't match. Re-run `release-kit rotate-tokens
--platform <slug>`.

## Audit hooks

Every token resolution emits a structlog event with the **source**:

```
INFO  resolve-token  source=keyring:release-kit:pypi
```

Ship the structured logs to your audit pipeline (Loki, Datadog,
CloudWatch) and alert on resolution from sources you didn't
expect (e.g. `source=env:RELEASE_KIT_TOKEN_PYPI` from a CI job
that's supposed to use OIDC).

## Don't

- Don't commit a `.env` (or any file containing tokens) to git.
  `release-kit init` adds `.env` to `.gitignore` for you.
- Don't share an automation token with a human session. Maintainer
  tokens and CI tokens are separate.
- Don't store production tokens in a personal password manager
  that other people can see by sharing a vault.
