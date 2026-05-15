# npm (public registry)

**Automation level**: OIDC + API
**Source-of-truth**: `package.json` `"version"`

## Overview

`registry.npmjs.org` is the canonical JavaScript / TypeScript /
Node.js registry. Free, unauthenticated read; authenticated writes
per package. Scoped packages (`@simtabi/release-kit`) and
unscoped (`release-kit`) supported.

## Account & project bootstrap

1. Register at `https://www.npmjs.com/signup`.
2. Enable 2FA: `Account Settings → Security → Two-Factor
   Authentication`. Choose **Auth-only** (required on a TOTP app)
   or **Auth and writes** (also gates publish). Auth-only is the
   recommended default; CI uses an automation token to bypass the
   second-factor prompt.
3. (Optional) Create an **organisation** for scoped packages:
   `New Org → free plan → scope name → my-org`. Scoped packages
   then publish as `@my-org/<pkg>`.

## Authentication options (ranked: most secure → least)

1. **OIDC + provenance** (GitHub Actions only) — `npm publish
   --provenance` derives identity from the workflow's ID-token.
2. **Granular access token** (UI: Settings → Access Tokens →
   "Generate New Token → Granular Access Token"). Pin to specific
   packages, set expiry, scope `Read and write`.
3. **Automation token** (UI: same flow, "Classic Token → Automation").
   Bypasses 2FA prompts; needed for unattended CI publishes if
   not using OIDC.
4. **Publish token** (classic). Prompts 2FA on every `npm publish`.
   Unsuitable for CI.
5. **Username + password** — only for browser login; never for
   `npm publish`.

## One-time setup

### OIDC + provenance (GitHub Actions)

```yaml
# bash / yaml
# .github/workflows/release.yml
name: release
on:
  push:
    tags: ['v*']

jobs:
  npm-publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm test
      - run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

Even with provenance, an `NPM_TOKEN` (granular access) is currently
required for the publish auth itself; provenance signs the artifact.

### Granular token (manual)

```bash
# bash
npm login                            # one-time, browser flow
# or set directly
echo "//registry.npmjs.org/:_authToken=npm_YOUR-TOKEN-HERE" >> ~/.npmrc
chmod 600 ~/.npmrc
```

## Per-release workflow

### Manual

```bash
# bash
# 1. Bump
$EDITOR package.json
npm version 1.4.2 --no-git-tag-version       # or just edit + commit

# 2. Test + build
npm ci
npm test
npm run build                                # if you have a build step

# 3. Pack-and-inspect (dry-run of publish)
npm pack --dry-run                           # shows the file list

# 4. Publish
npm publish --access public                  # for scoped, this is required
# or
npm publish --access restricted              # paid plan
```

### CI/CD

The OIDC + provenance workflow above triggers on `git push origin
v1.4.2`. Provenance attestations land in the published version's
metadata.

## Verification

```bash
# bash
# 1. Version listed
npm view simtabi-release-kit version

# 2. Installs
npm install simtabi-release-kit@1.4.2

# 3. Provenance
npm view simtabi-release-kit --json | jq '.dist.attestations'
# or
npm audit signatures
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `403 You must sign up for private packages` | Publishing a scoped package without `--access public` | Add `--access public` to `npm publish` |
| `402 Payment Required` | Scoped restricted package on free plan | Use `--access public` or upgrade |
| `403 You cannot publish over the previously published versions` | Re-publish of same version | Bump in `package.json` |
| `EPUBLISHCONFLICT` | Name squatted by someone else | Pick a different name or use a scope |
| `npm ERR! 401 Unauthorized` | Token stale / wrong registry | Verify `~/.npmrc`; check `npm config get registry` |
| Provenance step fails | `id-token: write` permission missing | Add to `permissions:` block in workflow |
| `package.json: spaces vs tabs` | Editor mangled the file | `npm pkg fix` repairs JSON |

## Security checklist

- [ ] 2FA enabled (Auth-only at minimum).
- [ ] Token is granular (per-package, expiring) or automation
      (CI only).
- [ ] Provenance enabled in CI.
- [ ] `.npmrc` in repo doesn't contain a real token (use `${NODE_AUTH_TOKEN}`).
- [ ] `package.json::files` whitelist is set so `npm pack` doesn't
      ship secrets accidentally.
- [ ] `.npmignore` exists (or `package.json::files` is set).

## See also

- [`npm-github.md`](npm-github.md) — same package, GitHub Packages registry
- [`npm-gitlab.md`](npm-gitlab.md) — same package, GitLab npm registry
- [`../cross-cutting/provenance.md`](../cross-cutting/provenance.md) —
  details on how npm provenance maps to Sigstore
