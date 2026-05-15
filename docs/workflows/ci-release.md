# Tag-driven CI release

Pushing a `vX.Y.Z` tag fans out to every enabled target.

## GitHub Actions

`.github/workflows/release.yml`:

```yaml
name: release
on:
  push:
    tags: ["v*"]

permissions:
  id-token: write    # OIDC for PyPI / GHCR / RubyGems
  contents: write    # Create GitHub releases
  packages: write    # GHCR push

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }   # for changelog scan + tag validation

      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }

      - run: pip install simtabi-release-kit

      - name: Doctor
        run: release-kit doctor

      - name: Publish
        run: release-kit publish --apply
        env:
          # Token fallback only — OIDC handles the rest.
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## GitLab CI

```yaml
release:
  stage: deploy
  rules: [{ if: $CI_COMMIT_TAG }]
  image: python:3.11-slim
  id_tokens:
    GITLAB_OIDC_TOKEN: { aud: https://gitlab.com }
  script:
    - pip install simtabi-release-kit
    - release-kit doctor
    - release-kit publish --apply
```

## What runs

1. `doctor` does an auth + validate sweep; CI fails fast on RED.
2. `publish --apply` walks every enabled target's full lifecycle.
3. Each platform's `verify` step re-fetches the artifact to confirm
   it's live.

## Token vs OIDC

OIDC-capable targets (PyPI, npm, GHCR, RubyGems, AWS ECR via
GitHub-OIDC) need no secrets in the CI store. The runner exchanges
an ephemeral ID token at publish time.

Token-only targets (Packagist, account-level NuGet, etc.) require
the platform's env var to be in the CI secret store. Set
`policies.allow_token_auth = true` for these projects, or run
`release-kit publish --allow-token-auth`.

## Re-running a partial failure

If 3 of 5 targets succeed and 2 fail, the report names exactly
which two. Fix the underlying cause, then re-run with `--target`
restricted to the unfinished targets:

```bash
release-kit publish --apply --target rubygems --target packagist
```

Targets that already published surface as
`status="skipped"` (idempotent platforms; see each platform's page)
or fail with a typed `code="version-already-published"` you can
catch.

## Concurrent merges

If multiple tags land in quick succession, the runner is
single-tag per invocation. Use a workflow concurrency block to
serialize:

```yaml
concurrency:
  group: release
  cancel-in-progress: false
```
