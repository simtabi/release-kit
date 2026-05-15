# GHCR (GitHub Container Registry)

| | |
|---|---|
| Class | `release_kit.platforms.registries.ghcr.GHCR` |
| Slug | `ghcr` |
| Automation | `OIDC_API` |
| Mixin | [`DockerPushMixin`](../../src/release_kit/platforms/mixins/docker_push.py) |

Workflow + onboarding + verification + common errors:
[`../playbook/registries/ghcr.md`](../playbook/registries/ghcr.md).

## Config

```json
"targets": {
  "ghcr": {
    "enabled": true,
    "auth": "oidc",
    "image": "ghcr.io/my-org/my-image",
    "tags": ["latest", "${VERSION}"],
    "env_var": "GITHUB_TOKEN",
    "platforms": ["linux/amd64", "linux/arm64"]
  }
}
```

| Key | Required | Default | Meaning |
|---|---|---|---|
| `image` | yes | — | Must start with `ghcr.io/` |
| `tags` | no | `["latest"]` | |
| `env_var` | no | `GITHUB_TOKEN` | |
| `platforms` | no | `linux/amd64,linux/arm64` | |

In GitHub Actions, the workflow's `GITHUB_TOKEN` is enough when
`permissions.packages: write` is set. No additional secret to manage.
