# GitLab Container Registry

**Automation level**: API
**Source-of-truth**: `Dockerfile`

## Overview

GitLab's built-in OCI registry at `registry.gitlab.com/<group>/<project>`
(or your self-managed instance). Per-project scoping; deep
integration with GitLab CI's `CI_JOB_TOKEN`.

## Account & project bootstrap

1. GitLab account / project exists.
2. **Settings → Packages and registries → Container Registry** —
   enable if disabled.
3. Group-level registry (for sharing across projects) is paid /
   self-managed; project-level is the default free path.

## Authentication options

1. **CI `CI_JOB_TOKEN`** — short-lived, automatic. Preferred for CI.
2. **Deploy Token** with `read_registry` / `write_registry` —
   scoped per-project or per-group.
3. **Project / Group Access Token** with `api` or
   `write_registry`.
4. **Personal Access Token** with `write_registry`.

## One-time setup

### CI (GitLab CI)

```yaml
# bash / yaml
# .gitlab-ci.yml
publish-image:
  stage: deploy
  image: docker:27
  services:
    - docker:27-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d/
  script:
    - echo "$CI_REGISTRY_PASSWORD" | docker login "$CI_REGISTRY" -u "$CI_REGISTRY_USER" --password-stdin
    - docker buildx create --use
    - docker buildx build
        --platform linux/amd64,linux/arm64
        --tag "$CI_REGISTRY_IMAGE:$CI_COMMIT_TAG"
        --tag "$CI_REGISTRY_IMAGE:latest"
        --push .
```

`CI_REGISTRY_USER`, `CI_REGISTRY_PASSWORD`, `CI_REGISTRY`, and
`CI_REGISTRY_IMAGE` are injected by GitLab automatically.

### Manual / local

```bash
# bash
docker login registry.gitlab.com -u <username>
# Password: a Deploy Token's secret value (recommended) or a PAT
```

## Per-release workflow

### Manual

```bash
# bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag registry.gitlab.com/<group>/<project>:1.4.2 \
  --tag registry.gitlab.com/<group>/<project>:latest \
  --push .
```

### CI/CD

Triggered by tag push per the rules block above.

## Verification

```bash
# bash
# 1. Web UI: Project → Deploy → Container Registry → expand the image
# 2. Pull (anonymous works for public projects)
docker pull registry.gitlab.com/<group>/<project>:1.4.2
# 3. Inspect manifest
docker buildx imagetools inspect registry.gitlab.com/<group>/<project>:1.4.2
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `denied: requested access to the resource is denied` | Deploy token missing `write_registry` scope | Regenerate with right scope |
| `name unknown: manifest unknown` | Tag was deleted via cleanup policy | Disable cleanup policy or extend retention |
| Image push times out | Self-managed GitLab without enough Pages/registry storage | Check instance disk; ask admin |
| `unauthorized: HTTP Basic: Access denied` | Username `oauth2` expected for some flows | Try `docker login -u oauth2 -p $CI_JOB_TOKEN registry.gitlab.com` |

## Security checklist

- [ ] CI uses `CI_JOB_TOKEN`, not a long-lived deploy token.
- [ ] Deploy tokens (if any) are read-only for consumers,
      write-only for publishers — never both.
- [ ] Cleanup policy configured to drop old tags
      (`Settings → Packages and registries → Cleanup policies`).
- [ ] Registry visibility matches project visibility.
- [ ] Image signed with `cosign` if your team adopts signing.

## See also

- [`dockerhub.md`](dockerhub.md), [`ghcr.md`](ghcr.md), [`aws-ecr.md`](aws-ecr.md)
- [GitLab Container Registry docs](https://docs.gitlab.com/ee/user/packages/container_registry/)
