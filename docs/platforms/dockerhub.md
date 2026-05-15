# Docker Hub

| | |
|---|---|
| Class | `release_kit.platforms.registries.dockerhub.DockerHub` |
| Slug | `dockerhub` |
| Automation | `FULL_API` (token; no OIDC support upstream) |
| Mixin | [`DockerPushMixin`](../../src/release_kit/platforms/mixins/docker_push.py) |

For the full workflow + onboarding + verification + common errors,
read [`../playbook/registries/dockerhub.md`](../playbook/registries/dockerhub.md).
This page covers only the release-kit config + Python surface.

## Config

```json
"targets": {
  "dockerhub": {
    "enabled": true,
    "auth": "token",
    "username": "my-dockerhub-user",
    "image": "my-namespace/my-image",
    "tags": ["latest", "${VERSION}"],
    "env_var": "DOCKERHUB_TOKEN",
    "platforms": ["linux/amd64", "linux/arm64"]
  }
}
```

| Key | Required | Default | Meaning |
|---|---|---|---|
| `username` | yes | — | Docker Hub username for `docker login` |
| `image` | yes | — | `<namespace>/<repo>` |
| `tags` | no | `["latest"]` | Tags to attach during build |
| `env_var` | no | `DOCKERHUB_TOKEN` | Env var holding the access token |
| `platforms` | no | `linux/amd64,linux/arm64` | buildx `--platform` list |

## Token scope

Docker Hub PATs with **Read, Write, Delete** on the namespace.
Do **not** use account password; 2FA breaks the flow. See
[`../playbook/cross-cutting/token-scoping.md::Docker Hub`](../playbook/cross-cutting/token-scoping.md).
