# Docker Hub

**Automation level**: API
**Source-of-truth**: `Dockerfile` / image build pipeline

## Overview

Docker Hub (`hub.docker.com`) is the original public OCI/Docker
image registry. Free for public images; rate-limited anonymous
pulls (200/6h) and authenticated (per-plan). Per-image visibility.

Image reference: `docker.io/<namespace>/<image>:<tag>` or
short form `<namespace>/<image>:<tag>`.

## Account & project bootstrap

1. Register at `https://hub.docker.com/signup`.
2. Enable 2FA: `Account Settings → Security`.
3. Reserve the namespace = your username, or create an organisation
   for `<org>/<image>` naming.

## Authentication options (ranked: most secure → least)

1. **Access token, per-namespace, scoped Read/Write/Delete** — set
   expiry, scope to specific repos.
2. **Access token, account-wide** — for first-time setup only.
3. **Username + password** — works but breaks under 2FA; deprecated.

Docker Hub does **not** support OIDC trusted publishing today.

## One-time setup

```bash
# bash
# Hub UI: Account Settings → Personal Access Tokens →
# "Generate New Token" → name release-kit-publish →
# Permissions: Read, Write, Delete -> generate, copy
```

```bash
# bash
docker login -u <hub-username>
# Password: dckr_pat_YOUR-TOKEN-HERE
```

The token is cached at `~/.docker/config.json` (Linux/macOS) or
the Windows Credential Manager. Confirm it's not stored plaintext:
`docker info | grep -i 'credential'`.

## Per-release workflow

### Manual (single-arch)

```bash
# bash
# 1. Build
docker build -t my-org/my-image:1.4.2 .
docker tag my-org/my-image:1.4.2 my-org/my-image:latest

# 2. Push
docker push my-org/my-image:1.4.2
docker push my-org/my-image:latest
```

### Manual (multi-arch via buildx)

```bash
# bash
docker buildx create --name multi --use --bootstrap

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag my-org/my-image:1.4.2 \
  --tag my-org/my-image:latest \
  --push .
```

### CI/CD (GitHub Actions)

```yaml
# bash / yaml
# .github/workflows/release.yml
publish-docker:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: docker/setup-qemu-action@v3
    - uses: docker/setup-buildx-action@v3
    - uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}
    - uses: docker/metadata-action@v5
      id: meta
      with:
        images: my-org/my-image
        tags: |
          type=semver,pattern={{version}}
          type=raw,value=latest,enable={{is_default_branch}}
    - uses: docker/build-push-action@v6
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
```

## Verification

```bash
# bash
# 1. Pull anonymously
docker pull my-org/my-image:1.4.2

# 2. Inspect manifest (architectures)
docker buildx imagetools inspect my-org/my-image:1.4.2

# 3. Web page lists tag
curl -fsSL "https://hub.docker.com/v2/repositories/my-org/my-image/tags/1.4.2/" | jq .
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `denied: requested access to the resource is denied` | Token missing Write permission OR repo doesn't exist | Verify token scope; create the repo via Hub UI |
| `unauthorized: authentication required` | Stale credentials in `~/.docker/config.json` | `docker logout && docker login` |
| Push hangs on a single layer | Network throttling or massive layer | Split the Dockerfile; check that no `COPY . .` of `node_modules` is happening |
| `manifest unknown` for `latest` | Pushed `:1.4.2` only | Tag separately and push: `docker tag ... :latest && docker push ... :latest` |
| Anonymous pull says "toomanyrequests" | Hub rate limit (200/6h) | `docker login` (auth'd users get higher limit) |
| ARM build hangs in QEMU | First-time emulator boot | Wait ~60s, or use a native ARM runner |

## Security checklist

- [ ] 2FA enabled on the publishing account.
- [ ] Token is per-namespace, not account-wide.
- [ ] Token has an expiry set (rotation cadence: 90 days).
- [ ] `latest` tag points at a SHA you can audit (`docker pull
      my-org/my-image:latest && docker images --digests`).
- [ ] Dockerfile starts with a base image pinned by digest
      (`FROM ubuntu@sha256:...`) or a stable tag, not `:latest`.
- [ ] Image scanned (`docker scout cves` or Trivy) before push in CI.
- [ ] No secrets in the image (`docker history`, `docker scout` reveal layers).
- [ ] Repository visibility (public vs. private) is correct.

## See also

- [`ghcr.md`](ghcr.md), [`gitlab-registry.md`](gitlab-registry.md),
  [`aws-ecr.md`](aws-ecr.md), [`gar.md`](gar.md), [`acr.md`](acr.md)
  — alternative OCI registries
- [`../cross-cutting/provenance.md`](../cross-cutting/provenance.md) — `cosign` signing for OCI artifacts
