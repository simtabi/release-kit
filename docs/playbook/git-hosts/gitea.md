# Gitea / Forgejo

**Automation level**: API
**Source-of-truth**: per-instance settings + workflows

## Overview

Gitea is a lightweight self-hosted git server with a GitHub-like
API. Forgejo is a community fork of Gitea (Codeberg runs Forgejo);
their APIs are compatible.

REST API at `https://<host>/api/v1/`. CLI: `tea` (Gitea) or
`forgejo-cli` (Forgejo); both can target either backend.

## Account & project bootstrap

1. Have a Gitea / Forgejo instance (`https://codeberg.org` is a
   free Forgejo for OSS).
2. Generate API token: User Settings → **Applications →
   Generate New Token**. Pick scopes.
3. Create repo:

```bash
# bash
tea repo create --name release-kit --description "..." \
  --owner my-org --visibility public

# Or via API
curl -fsSL -XPOST -H "Authorization: token <token>" \
  "https://gitea.example.com/api/v1/orgs/my-org/repos" \
  -d '{"name":"release-kit","description":"...","private":false,"auto_init":true}'
```

## Authentication options (ranked)

1. **Workflow `GITEA_TOKEN`** (Gitea Actions, since 1.20) — short-lived,
   auto-injected.
2. **OAuth 2.0** for third-party apps.
3. **Personal Access Token** with scoped permissions (repo, packages, etc.).

OIDC is supported as an **OAuth 2.0 provider** (Gitea / Forgejo
can be the issuer for downstream consumers). Inbound OIDC from
external CI providers is being added gradually.

## One-time setup

### Repo settings

```bash
# bash
# Edit description, topics, etc.
curl -fsSL -XPATCH \
  -H "Authorization: token <token>" \
  -H "Content-Type: application/json" \
  "https://gitea.example.com/api/v1/repos/my-org/release-kit" \
  -d '{"description":"Multi-registry publishing automation"}'

# Add topics
curl -fsSL -XPUT \
  -H "Authorization: token <token>" \
  -H "Content-Type: application/json" \
  "https://gitea.example.com/api/v1/repos/my-org/release-kit/topics" \
  -d '{"topics":["oss","python","publishing"]}'
```

### Branch protection

```bash
# bash
curl -fsSL -XPOST \
  -H "Authorization: token <token>" \
  -H "Content-Type: application/json" \
  "https://gitea.example.com/api/v1/repos/my-org/release-kit/branch_protections" \
  -d '{
    "branch_name": "main",
    "enable_push": false,
    "require_signed_commits": false,
    "required_approvals": 1
  }'
```

## Per-release workflow

### Manual

```bash
# bash
git push origin v1.4.2

# Create release
curl -fsSL -XPOST \
  -H "Authorization: token <token>" \
  -H "Content-Type: application/json" \
  "https://gitea.example.com/api/v1/repos/my-org/release-kit/releases" \
  -d '{
    "tag_name": "v1.4.2",
    "name": "v1.4.2",
    "body": "release notes",
    "draft": false,
    "prerelease": false
  }'

# Upload asset
RELEASE_ID=$(curl -fsSL -H "Authorization: token <token>" \
  "https://gitea.example.com/api/v1/repos/my-org/release-kit/releases/tags/v1.4.2" \
  | jq -r .id)
curl -fsSL -XPOST \
  -H "Authorization: token <token>" \
  "https://gitea.example.com/api/v1/repos/my-org/release-kit/releases/$RELEASE_ID/assets" \
  -F "attachment=@dist/release-kit-1.4.2.tar.gz"
```

### CI/CD (Gitea Actions — GitHub-Actions-compatible)

```yaml
# bash / yaml
# .gitea/workflows/release.yml
on:
  push:
    tags: ['v*']
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: |
          pip install build twine
          python -m build
          twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

`secrets.GITEA_TOKEN` is auto-injected like GitHub's
`secrets.GITHUB_TOKEN`.

## Verification

```bash
# bash
# Tag + release object
curl -fsSL "https://gitea.example.com/api/v1/repos/my-org/release-kit/releases/tags/v1.4.2" | jq .name

# Clone works
git clone https://gitea.example.com/my-org/release-kit.git
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `404 Not Found` on `releases/tags/<tag>` | Tag pushed but no release object | Create the release object explicitly per script above |
| Gitea Actions runner offline | Runner needs registration | Admin: Site administration → Actions → Runners; register a new runner with `act_runner` |
| Token-scope error | Token lacks `write:repository` or `write:package` | Regenerate with right scope |
| `tea` CLI doesn't see new repo | Stale `~/.tea` config | `tea logout && tea login` |

## Security checklist

- [ ] 2FA enabled.
- [ ] Tokens scoped narrowly; expire annually.
- [ ] Branch protection enabled with required reviews.
- [ ] Signed commits required for `main` (optional but supported).
- [ ] Instance on a current minor version.
- [ ] Admin access via separate account from publishing.

## See also

- [Gitea API docs](https://docs.gitea.com/api)
- [Forgejo docs](https://forgejo.org/docs/)
- [Gitea Actions](https://docs.gitea.com/usage/actions/overview) — GitHub-compatible
