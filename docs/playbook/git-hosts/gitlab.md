# GitLab.com

**Automation level**: OIDC + API
**Source-of-truth**: project settings + `.gitlab-ci.yml`

## Overview

`gitlab.com` is the SaaS GitLab. Source repos, issues, merge requests,
releases, packages (npm, Maven, Container Registry, etc.), GitLab CI.
REST API v4; `glab` CLI as the canonical wrapper.

This page covers project-level automation. Per-platform package
publishing lives under [`../registries/`](../registries/) (the GitLab-hosted
registries: `npm-gitlab`, `gitlab-registry`).

## Account & project bootstrap

1. Account at `https://gitlab.com/users/sign_up`.
2. Enable 2FA: `Edit profile → Account → Two-Factor Authentication`.
3. Authenticate `glab`: `glab auth login`.
4. Create the project:

```bash
# bash
glab repo create my-group/release-kit --public \
  --description "Multi-registry publishing automation"
```

Or via API:

```bash
# bash
curl -fsSL -XPOST -H "PRIVATE-TOKEN: $GL_TOKEN" \
  https://gitlab.com/api/v4/projects \
  -F name="release-kit" -F namespace_id="<group-id>" -F visibility=public
```

## Authentication options (ranked: most secure → least)

1. **CI `CI_JOB_TOKEN`** — short-lived, auto-injected in
   `.gitlab-ci.yml`. Limited cross-project scope by default.
2. **OIDC ID-token** via `id_tokens:` in CI — federates to AWS,
   GCP, Azure, PyPI, etc.
3. **Project Access Token** with the required scope. Per-project,
   expiring.
4. **Group Access Token** with required scope. Per-group, expiring.
5. **Deploy Token** with `read_registry` / `write_repository` etc.
   For pull-only consumers or single-purpose pushers.
6. **Personal Access Token (PAT)** with `api` scope. Broadest;
   prefer the above.

## One-time setup

### Repo settings via API

```bash
# bash
# Topics + description
glab api projects/my-group%2Frelease-kit --method PUT \
  --field description="Multi-registry publishing automation" \
  --field topics="oss,python,publishing,ci-cd"

# Default branch
glab api projects/my-group%2Frelease-kit --method PUT \
  --field default_branch=main

# Merge method
glab api projects/my-group%2Frelease-kit --method PUT \
  --field merge_method=ff                 # fast-forward; alternatives: merge, rebase_merge
```

### Branch protection on `main`

```bash
# bash
glab api projects/my-group%2Frelease-kit/protected_branches \
  --method POST \
  --field name=main \
  --field push_access_level=40                 # 40 = maintainer
  --field merge_access_level=40 \
  --field allow_force_push=false
```

### CI / OIDC

```yaml
# bash / yaml
# .gitlab-ci.yml
default:
  image: alpine:latest

stages:
  - test
  - deploy

test:
  stage: test
  script:
    - apk add --no-cache python3
    - python3 --version

publish:
  stage: deploy
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d/
  id_tokens:
    PYPI_ID_TOKEN:
      aud: pypi
  script:
    - echo "publishing $CI_COMMIT_TAG"
    # See ../registries/pypi.md for the actual publish step
```

## Per-release workflow

### Manual

```bash
# bash
# Push commit + tag
git add -u
git commit -m "release: v1.4.2"
git tag -a v1.4.2 -m "v1.4.2"
git push origin main
git push origin v1.4.2

# Create the GitLab release object
glab release create v1.4.2 --notes-file release-notes.md \
  --asset dist/release-kit-1.4.2.tar.gz
```

### CI/CD (auto-release on tag push)

```yaml
# bash / yaml
publish-release:
  stage: deploy
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d/
  script:
    - apk add --no-cache curl jq
    - |
      curl --fail --header "PRIVATE-TOKEN: $CI_API_TOKEN" \
        --request POST "$CI_API_V4_URL/projects/$CI_PROJECT_ID/releases" \
        --data-urlencode "name=$CI_COMMIT_TAG" \
        --data-urlencode "tag_name=$CI_COMMIT_TAG" \
        --data "ref=$CI_COMMIT_SHA"
```

## Verification

```bash
# bash
# 1. Release object exists
glab release view v1.4.2

# 2. Pipeline succeeded
glab ci view --branch v1.4.2

# 3. Branch protection
glab api projects/my-group%2Frelease-kit/protected_branches/main
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `403 Forbidden` on API push | PAT missing `api` scope | Regenerate; project / group access tokens are usually narrower than `api` |
| `Branch is protected from force push` | Trying to force-push to `main` | Push to a branch, open MR; don't force-push protected refs |
| OIDC token rejected | Audience claim mismatch | Set `aud` in `id_tokens` to match consumer's expected audience |
| `Forbidden: You are not allowed to push code` | Group / project membership insufficient | Maintainer access required for protected branches |
| `Pipeline failed: configuration is invalid` | `.gitlab-ci.yml` syntax | `glab ci lint` |

## Security checklist

- [ ] 2FA enabled on the publishing account.
- [ ] Branch protection on `main` (no force-push, maintainer-only).
- [ ] `CI_JOB_TOKEN` permissions reviewed
      (Settings → CI/CD → Job token permissions).
- [ ] Project Access Tokens / Group Access Tokens expire.
- [ ] No PATs in CI variables (prefer scoped tokens).
- [ ] Approval rules require ≥1 reviewer on `main`.
- [ ] Container Scanning + Dependency Scanning enabled (Premium).

## See also

- [`gitlab-self-managed.md`](gitlab-self-managed.md) — same API,
  per-instance.
- [`../registries/npm-gitlab.md`](../registries/npm-gitlab.md),
  [`../registries/gitlab-registry.md`](../registries/gitlab-registry.md)
- [GitLab REST API](https://docs.gitlab.com/ee/api/)
- [`glab` docs](https://gitlab.com/gitlab-org/cli)
