# GitHub.com

**Automation level**: OIDC + API
**Source-of-truth**: repo settings + workflows in `.github/`

## Overview

`github.com` is the consumer GitHub. Hosts source repositories,
issues, PRs, releases, packages (GHCR, npm, Maven, etc.),
Actions, GitHub Pages. Full REST + GraphQL APIs; `gh` CLI as the
canonical wrapper.

This page covers repo-level automation: creating repos, managing
topics, branch protection, releases, secrets/environments,
webhooks. Per-platform package publishing lives under
[`../registries/`](../registries/).

## Account & project bootstrap

1. Create or use existing GitHub user / organisation.
2. Authenticate `gh` CLI: `gh auth login` (browser or token).
3. Create the repo:

```bash
# bash
gh repo create simtabi/release-kit --public \
  --description "Multi-registry publishing automation" \
  --homepage "https://github.com/simtabi/release-kit" \
  --license MIT \
  --source=. --remote=origin --push
```

## Authentication options (ranked: most secure → least)

1. **Workflow `GITHUB_TOKEN`** — auto-injected in Actions,
   workflow-scoped, expires when the job ends.
2. **OIDC ID-token** for cross-platform trust (PyPI, AWS, GCP,
   Azure) — `permissions: id-token: write`.
3. **Fine-grained PAT** — per-repo or per-org scope, expiring.
4. **Classic PAT** — broad scopes (`repo`, `workflow`,
   `write:packages`). Avoid.
5. **OAuth App** — for third-party integrations only.

## One-time setup

### Repo settings (via gh CLI)

```bash
# bash
# Description + homepage + topics
gh repo edit simtabi/release-kit \
  --description "Multi-registry publishing automation" \
  --homepage "https://github.com/simtabi/release-kit" \
  --add-topic oss --add-topic python --add-topic publishing \
  --add-topic ci-cd --add-topic release-automation

# Default branch
gh api -X PATCH /repos/simtabi/release-kit -f default_branch=main

# Issue templates, discussions, etc.
gh api -X PATCH /repos/simtabi/release-kit \
  -F has_issues=true -F has_discussions=true \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true
```

### Branch protection on `main`

```bash
# bash
gh api -X PUT /repos/simtabi/release-kit/branches/main/protection \
  --field 'required_status_checks[strict]=true' \
  --field 'required_status_checks[contexts][]=ci / test' \
  --field 'required_status_checks[contexts][]=ci / lint' \
  --field 'enforce_admins=false' \
  --field 'required_pull_request_reviews[required_approving_review_count]=1' \
  --field 'required_pull_request_reviews[dismiss_stale_reviews]=true' \
  --field 'required_pull_request_reviews[require_code_owner_reviews]=false' \
  --field 'restrictions=null' \
  --field 'allow_force_pushes=false' \
  --field 'allow_deletions=false'
```

### Environments (for OIDC + required reviewers)

```bash
# bash
# Create environment
gh api -X PUT /repos/simtabi/release-kit/environments/pypi

# Add required reviewers (humans gate the deploy)
gh api -X PUT /repos/simtabi/release-kit/environments/pypi \
  -F 'reviewers[][type]=User' -F 'reviewers[][id]=1234567'
```

## Per-release workflow

### Manual release

```bash
# bash
# Create release from tag, generate notes from PRs since last release
gh release create v1.4.2 \
  --title "v1.4.2 - one-line summary" \
  --generate-notes \
  --notes-file release-notes.md \
  dist/*                                # attach build artifacts as assets
```

### CI/CD (auto-release on tag push)

```yaml
# bash / yaml
# .github/workflows/release.yml
name: release
on:
  push:
    tags: ['v*']

jobs:
  publish-pypi:    # see ../registries/pypi.md
    ...
  github-release:
    needs: publish-pypi
    runs-on: ubuntu-latest
    permissions:
      contents: write       # required to create the release
    steps:
      - uses: actions/checkout@v4
      - uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          fail_on_unmatched_files: true
          files: |
            dist/*.whl
            dist/*.tar.gz
```

### Webhooks (push notifications to external services)

```bash
# bash
# Add a webhook -- e.g., Packagist
gh api -X POST /repos/simtabi/release-kit/hooks \
  -f name=web \
  -f 'config[url]=https://packagist.org/api/github?username=simtabi' \
  -f 'config[content_type]=json' \
  -f 'config[secret]=PACKAGIST-TOKEN' \
  -F 'events[]=push' -F 'events[]=release' \
  -f active=true
```

## Verification

```bash
# bash
# 1. Release page exists
gh release view v1.4.2

# 2. Tag pushed
git ls-remote --tags origin | grep v1.4.2

# 3. Branch protection active
gh api /repos/simtabi/release-kit/branches/main/protection | jq .url

# 4. Topics + description visible
gh repo view simtabi/release-kit --json description,homepageUrl,repositoryTopics
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `gh: GraphQL: Resource not accessible by integration` | Workflow lacks the right `permissions:` | Add `contents: write` / `packages: write` etc. |
| `Branch is protected` on push | Direct push to protected `main` | Open a PR; merge after review |
| Release notes empty | `--generate-notes` requires PRs since last release | Manually pass `--notes-file` for the first release |
| OIDC consumer rejects token | Wrong `aud` or `sub` claim | Inspect with [`jwt.io`](https://jwt.io); update the consumer's trust policy |
| `Resource not accessible by personal access token` | Fine-grained PAT missing the right resource scope | Re-issue with `Contents: Read & write` etc. |

## Security checklist

- [ ] Branch protection on `main` (≥1 review, status checks, no
      force-push, no deletion).
- [ ] Required environments for deploy jobs (publish-to-PyPI,
      publish-to-tap).
- [ ] `Settings → Actions → General → Workflow permissions = Read`
      with explicit `permissions:` blocks per workflow.
- [ ] Allowed actions list restricted to a curated set (no
      `*` wildcard).
- [ ] Default Dependabot enabled for `actions`, `github-actions`,
      `<your-package-ecosystem>`.
- [ ] Code scanning + Secret scanning enabled
      (`Settings → Code security`).
- [ ] No long-lived PATs in `secrets`; prefer environment-scoped
      OIDC.

## See also

- [`github-enterprise-cloud.md`](github-enterprise-cloud.md) — same API, different SLA + admin
- [`github-enterprise-server.md`](github-enterprise-server.md) — self-hosted GitHub
- [`../registries/ghcr.md`](../registries/ghcr.md) — packages on GitHub
- [GitHub REST API](https://docs.github.com/en/rest)
- [`gh` CLI manual](https://cli.github.com/manual/)
