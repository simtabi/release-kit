# GHCR (GitHub Container Registry)

**Automation level**: OIDC + API
**Source-of-truth**: `Dockerfile`

## Overview

GHCR (`ghcr.io`) hosts OCI / Docker images alongside GitHub source
repos. Free for public images on public repos; per-namespace
permissions tied to GitHub identities. Image reference:
`ghcr.io/<owner>/<image>:<tag>`.

GHCR is generally the lowest-friction OCI host for projects already
on GitHub.

## Account & project bootstrap

1. GitHub account or org exists.
2. First push creates the package; no pre-claim step.
3. After first push, set visibility (public / internal / private)
   at `https://github.com/<owner>/<image>/packages` → package →
   **Package settings → Change visibility**.

## Authentication options (ranked: most secure → least)

1. **Workflow `GITHUB_TOKEN`** in GitHub Actions with
   `permissions: packages: write`. Short-lived, repo-scoped.
2. **Fine-grained PAT** with **Packages: Read & write**.
3. **Classic PAT** with `write:packages` (and `read:packages` for
   pull).
4. **OIDC via `docker/login-action`** + a GHCR-supported claim
   binding (experimental for cross-org).

## One-time setup

### CI (GitHub Actions, GITHUB_TOKEN)

```yaml
# bash / yaml
# .github/workflows/release.yml
publish-ghcr:
  runs-on: ubuntu-latest
  permissions:
    contents: read
    packages: write       # this enables GHCR push
  steps:
    - uses: actions/checkout@v4
    - uses: docker/setup-qemu-action@v3
    - uses: docker/setup-buildx-action@v3
    - uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    - uses: docker/metadata-action@v5
      id: meta
      with:
        images: ghcr.io/${{ github.repository }}
        tags: |
          type=semver,pattern={{version}}
          type=sha,format=long
          type=raw,value=latest,enable={{is_default_branch}}
    - uses: docker/build-push-action@v6
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
```

### Manual / local (PAT)

```bash
# bash
# GitHub UI: Settings → Developer settings → Personal access tokens
# → Fine-grained tokens → Generate → Repository access: this repo
# → Permissions: Packages: Read & write
echo "ghp_YOUR-TOKEN-HERE" | docker login ghcr.io -u <your-user> --password-stdin
```

## Per-release workflow

### Manual

```bash
# bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ghcr.io/simtabi/release-kit:1.4.2 \
  --tag ghcr.io/simtabi/release-kit:latest \
  --push .
```

### CI/CD

The workflow above triggers on tag push or main branch.

## Verification

```bash
# bash
# 1. Package page exists at:
# https://github.com/orgs/simtabi/packages?repo_name=release-kit

# 2. Pull (anonymous works for public packages)
docker pull ghcr.io/simtabi/release-kit:1.4.2

# 3. Inspect provenance (if signed with cosign)
cosign verify ghcr.io/simtabi/release-kit:1.4.2 \
  --certificate-identity-regexp 'https://github.com/simtabi/release-kit/.+' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `denied: permission_denied: write_package` | Workflow missing `packages: write` | Add to `permissions:` |
| `denied: installation not allowed to Create organization package` | Org has restricted GHCR creation | Org settings → Member privileges → Allow members to create packages |
| Anonymous pull fails on public package | Package is still private | Package settings → Change visibility → Public |
| Stale image pulled despite new push | Local Docker cache | `docker pull ghcr.io/...:tag` to force; or use SHA |
| `manifest schema 1` not supported | Old Docker daemon pushing v1 manifests | Use BuildKit / buildx |

## Security checklist

- [ ] CI uses `GITHUB_TOKEN` with workflow-scoped `packages: write`.
- [ ] Long-lived PATs (if any) are fine-grained and expire.
- [ ] Package visibility is reviewed for each new image.
- [ ] Images signed with `cosign` per [`../cross-cutting/provenance.md`](../cross-cutting/provenance.md).
- [ ] No secrets in image layers (`docker history`, `docker scout`).
- [ ] `latest` tag isn't pinned by external consumers in production.

## See also

- [`dockerhub.md`](dockerhub.md), [`gitlab-registry.md`](gitlab-registry.md),
  [`aws-ecr.md`](aws-ecr.md) — alternatives.
- [`../cross-cutting/provenance.md`](../cross-cutting/provenance.md) — cosign + OIDC signing.
