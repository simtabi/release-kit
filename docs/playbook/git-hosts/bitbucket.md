# Bitbucket Cloud

**Automation level**: API
**Source-of-truth**: workspace + repository settings

## Overview

Bitbucket Cloud (`bitbucket.org`) is Atlassian's SaaS git host.
Workspaces (top-level) contain projects (optional grouping)
contain repos. REST API v2.0 at `api.bitbucket.org`.

## Account & project bootstrap

1. Account at `https://bitbucket.org/account/signup`.
2. Create a workspace (free tier: 5 users, unlimited public repos).
3. Authenticate (no first-party CLI; use `curl` or the
   community `bb` tool):

```bash
# bash
# Create repo via API
curl -fsSL -XPOST \
  -u "<user>:<app-password>" \
  "https://api.bitbucket.org/2.0/repositories/<workspace>/release-kit" \
  -H "Content-Type: application/json" \
  -d '{"scm":"git","is_private":false,"description":"Multi-registry publishing automation"}'
```

## Authentication options (ranked: most secure → least)

1. **Bitbucket Pipelines OIDC** — workspace-level federation to
   AWS, GCP, Azure. Workspace settings → OpenID Connect.
2. **Workspace Access Token** (since 2023) — scoped, expiring,
   not tied to a user.
3. **Project Access Token** — same shape, project-scoped.
4. **Repository Access Token** — narrowest of the three.
5. **App password** (per-user) — works, but ties automation to a
   user account.
6. **OAuth 2.0 client credentials** — for third-party integrations.

## One-time setup

### Workspace OIDC for AWS

```bash
# bash
# 1. Bitbucket Pipelines auto-exposes BITBUCKET_STEP_OIDC_TOKEN in pipeline steps.
# 2. Issuer URL is: https://api.bitbucket.org/2.0/workspaces/<workspace>/pipelines-config/identity/oidc
# 3. Create the IAM OIDC provider:
aws iam create-open-id-connect-provider \
  --url "https://api.bitbucket.org/2.0/workspaces/<workspace>/pipelines-config/identity/oidc" \
  --client-id-list "ari:cloud:bitbucket::workspace/<workspace-uuid>"
```

Trust policy `sub` claim:
`<workspace-uuid>:<repo-uuid>:env:<deployment-env>`.

### App password (manual fallback)

Account Settings → **App passwords → Create**:

- Label: `release-kit-publish`
- Permissions: Repositories: Write; Pipelines: Edit variables
- Copy the password (shown once).

## Per-release workflow

### Manual

```bash
# bash
git push origin v1.4.2

# Create a release (Bitbucket has no first-class "Release" object
# like GitHub; the convention is a tag + a downloads upload)
curl -fsSL -XPOST -u "<user>:<app-password>" \
  "https://api.bitbucket.org/2.0/repositories/<workspace>/release-kit/downloads" \
  -F "files=@dist/release-kit-1.4.2.tar.gz"
```

### CI/CD (Bitbucket Pipelines)

```yaml
# bash / yaml
# bitbucket-pipelines.yml
image: python:3.13

pipelines:
  tags:
    'v*':
      - step:
          name: Publish to PyPI
          oidc: true                  # exposes BITBUCKET_STEP_OIDC_TOKEN
          script:
            - pip install build twine
            - python -m build
            - twine upload -u __token__ -p "$PYPI_TOKEN" dist/*
```

## Verification

```bash
# bash
# 1. Tag pushed
git ls-remote --tags origin | grep v1.4.2

# 2. Download artifact present
curl -fsSL -u "<user>:<app-password>" \
  "https://api.bitbucket.org/2.0/repositories/<workspace>/release-kit/downloads" \
  | jq '.values[].name'

# 3. Pipeline succeeded
# Bitbucket UI: Repository → Pipelines
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | App password expired or revoked | Generate a new one |
| `Repository not found` | Workspace slug wrong (case-sensitive in some contexts) | Look up exact slug in the URL |
| OIDC token rejected | Trust policy `sub` claim format wrong | Inspect the actual JWT; format is `<workspace-uuid>:<repo-uuid>:...` |
| `bitbucket-pipelines.yml` parse error | Tabs / wrong indentation | Validate with the in-UI editor (squiggle-lints inline) |
| Can't merge PR with insufficient builds | Default branch needs ≥1 green build | Set up Pipelines for the project |

## Security checklist

- [ ] 2FA enabled on Bitbucket account.
- [ ] App passwords scoped narrowly; expire annually.
- [ ] Workspace OIDC configured for AWS / GCP / Azure where
      applicable.
- [ ] Branch restrictions: prevent rewriting history, require
      passing pipelines, require PR review.
- [ ] No long-lived OAuth clients with broad scopes.

## See also

- [`bitbucket-dc.md`](bitbucket-dc.md) — self-hosted Bitbucket Data Center
- [Bitbucket Cloud REST API](https://developer.atlassian.com/cloud/bitbucket/rest/)
- [Bitbucket Pipelines OIDC](https://support.atlassian.com/bitbucket-cloud/docs/integrate-pipelines-with-resource-servers-using-oidc/)
