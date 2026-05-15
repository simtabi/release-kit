# npm via GitHub Packages

**Automation level**: API
**Source-of-truth**: `package.json` `"version"`

## Overview

GitHub Packages hosts npm packages at `npm.pkg.github.com`,
scoped to a GitHub org or user. Useful for **internal / private**
packages on GitHub-hosted source repos; public packages typically
stay on `registry.npmjs.org` for discovery.

Package URL: `https://npm.pkg.github.com/@<owner>/<pkg>`.

## Account & project bootstrap

1. Already have a GitHub account.
2. Scoped name format **must** match the org/user: an account
   `simtabi` publishes only `@simtabi/<pkg>`. No unscoped names.
3. Decide visibility: package inherits the source repo's visibility
   by default. Public packages need `read:packages` for anonymous
   install.

## Authentication options

1. **Workflow `GITHUB_TOKEN`** (in CI on GitHub Actions) — short-
   lived, scoped to the repo. Cleanest.
2. **Fine-grained PAT** — Packages: Read & write; optional repo
   scope.
3. **Classic PAT** — `write:packages` scope (and `read:packages`
   for install).

## One-time setup

### CI

```yaml
# bash / yaml
# .github/workflows/release.yml
publish-gh:
  runs-on: ubuntu-latest
  permissions:
    contents: read
    packages: write          # this is the only required scope
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        registry-url: 'https://npm.pkg.github.com'
        scope: '@simtabi'
    - run: npm ci
    - run: npm publish
      env:
        NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

`setup-node`'s `registry-url` and `scope` together write the right
`.npmrc` for you.

### Manual / local

```bash
# bash
# ~/.npmrc
@simtabi:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=ghp_YOUR-PAT-HERE
```

Or use a per-project `.npmrc` in the repo (gitignored) for dev.

## Per-release workflow

### Manual

```bash
# bash
$EDITOR package.json                          # bump version
npm version 1.4.2 --no-git-tag-version
npm publish                                   # picks scope+registry from .npmrc
```

### CI/CD

The workflow above triggers on tag push; uses `GITHUB_TOKEN`.

## Verification

```bash
# bash
# 1. Package page exists at:
# https://github.com/orgs/simtabi/packages?repo_name=release-kit

# 2. Install (consumer needs PAT to read private packages)
npm install @simtabi/release-kit@1.4.2
# Consumer's ~/.npmrc must have an auth token for npm.pkg.github.com
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `404 Not Found - PUT` | Scope ≠ org | Rename to `@<your-org>/<pkg>` |
| `401 Unauthorized` | Token missing `packages:write` | Add scope to PAT |
| `403 Forbidden` | Token belongs to a user with no package perm | Check `actions:write` on the workflow if private |
| `409 Conflict: package_name` | Trying to publish same name to two registries | npmjs.org vs GitHub Packages — choose one, or use distinct scopes |
| `install` fails as anonymous on public package | GitHub Packages defaults to private | Set the package public via `Package settings → Change visibility` |

## Security checklist

- [ ] CI uses `GITHUB_TOKEN`, not a long-lived PAT.
- [ ] Per-package visibility reviewed; private by default.
- [ ] Repo settings → Actions → workflow permissions allow
      packages write.
- [ ] PAT (if used) is fine-grained and expires.

## See also

- [`npm.md`](npm.md) — public registry equivalent
- [`ghcr.md`](ghcr.md) — same auth model, OCI artifacts
