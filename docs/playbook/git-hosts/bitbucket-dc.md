# Bitbucket Data Center

**Automation level**: API
**Source-of-truth**: same as [`bitbucket.md`](bitbucket.md)

## Overview

Bitbucket Data Center is Atlassian's self-hosted/on-prem Bitbucket
(separate from Bitbucket Cloud). **Different REST API** than Cloud:
v1.0 / v2.0 endpoints under `/rest/api/1.0/`.

This page covers deltas from [`bitbucket.md`](bitbucket.md).

## Account & project bootstrap

1. Get hostname + sign-in from your admin.
2. No public-cloud sign-up; LDAP / Crowd / SAML via the instance.
3. Projects (top-level) contain repositories (no "workspace" layer):

```bash
# bash
curl -fsSL -XPOST \
  -u "<user>:<pat>" \
  "https://bitbucket.example.com/rest/api/1.0/projects/PROJ/repos" \
  -H "Content-Type: application/json" \
  -d '{"name":"release-kit","scmId":"git","forkable":true,"public":false}'
```

## Authentication options

1. **HTTP Access Tokens** (since BBDC 8.0+) — per-repo or
   per-project, scoped, expiring.
2. **Personal Access Tokens (PAT)** — per-user, scoped.
3. **App passwords** — same model as Bitbucket Cloud.
4. **OAuth 2.0** — for third-party integrations.

OIDC is **not** supported by Bitbucket Data Center as of 2025.

## One-time setup

### Per-repository Access Token

UI: Repository → Settings → **Access tokens → Create**:

- Token name: `release-kit-publish`
- Permissions: Project read, Repo write
- Expiry: 6 months

The token is shown once; copy + store per
[`../cross-cutting/secrets.md`](../cross-cutting/secrets.md).

## Per-release workflow

### Manual

```bash
# bash
git push origin v1.4.2

# Upload artifact attachments (uses Stash REST API)
curl -fsSL -XPOST \
  -H "Authorization: Bearer <token>" \
  "https://bitbucket.example.com/rest/api/1.0/projects/PROJ/repos/release-kit/downloads" \
  -F "file=@dist/release-kit-1.4.2.tar.gz"
```

### CI/CD (Bamboo / Jenkins / external runner)

Bitbucket Data Center doesn't have a built-in CI runner. Pair with:

- **Bamboo** (Atlassian's self-hosted CI)
- **Jenkins** with the Bitbucket Server plugin
- **GitHub Actions** triggered by a Bitbucket webhook (cross-host)

Webhook setup:

```bash
# bash
curl -fsSL -XPOST -H "Authorization: Bearer <token>" \
  "https://bitbucket.example.com/rest/api/1.0/projects/PROJ/repos/release-kit/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "release-trigger",
    "active": true,
    "events": ["repo:refs_changed"],
    "url": "https://my-bamboo.example.com/webhook"
  }'
```

## Verification

```bash
# bash
# Tag pushed
git ls-remote --tags origin | grep v1.4.2

# Repo readable
curl -fsSL -H "Authorization: Bearer <token>" \
  "https://bitbucket.example.com/rest/api/1.0/projects/PROJ/repos/release-kit/branches"
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` despite valid token | Wrong API path (using Cloud v2.0 syntax on DC) | DC API is `/rest/api/1.0/`; pulls + pushes are git, but REST differs |
| `403 Insufficient permissions` | Token's project-scope doesn't cover this repo | Generate at the repo level |
| Push hangs over corporate VPN | MTU / proxy issue | Confirm `git config http.postBuffer 524288000`; check proxy |
| Audit log not capturing token use | DC audit-log retention configurable | Admin: extend retention |

## Security checklist

- [ ] Tokens are HTTP Access Tokens (per-repo), not user PATs.
- [ ] Tokens expire ≤ 6 months.
- [ ] Branch permissions configured (write access restricted).
- [ ] Pull-request reviewers enforced via "default reviewers".
- [ ] Audit logs streaming to your SIEM.
- [ ] DC version on a supported track (LTS).

## See also

- [`bitbucket.md`](bitbucket.md) — Bitbucket Cloud (different API)
- [Bitbucket Data Center REST API](https://developer.atlassian.com/server/bitbucket/reference/rest-api/)
