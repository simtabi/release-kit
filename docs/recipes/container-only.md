# Container image → GHCR + Docker Hub + AWS ECR

A multi-registry container push. No language package; image only.

## `release.json`

```json
{
  "project": {
    "name": "my-service",
    "version_source": "git-tag"
  },
  "targets": {
    "ghcr": {
      "enabled": true,
      "auth": "oidc",
      "image": "ghcr.io/my-org/my-service",
      "tags": ["1.4.0", "latest"]
    },
    "dockerhub": {
      "enabled": true,
      "auth": "token",
      "username": "my-org",
      "image": "my-org/my-service",
      "tags": ["1.4.0", "latest"]
    },
    "aws-ecr": {
      "enabled": true,
      "auth": "oidc",
      "registry": "123456789012.dkr.ecr.us-east-1.amazonaws.com",
      "image": "my-service",
      "tags": ["1.4.0", "latest"]
    }
  },
  "policies": {
    "default_dry_run": true,
    "continue_on_error": false
  }
}
```

## Workflow

```yaml
name: release
on: { push: { tags: ["v*"] } }
permissions:
  id-token: write
  contents: read
  packages: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/release-kit-pusher
          aws-region: us-east-1
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install simtabi-release-kit
      - run: release-kit publish --apply
```

## Notes

- Docker Hub doesn't support OIDC. Set `DOCKERHUB_TOKEN` in the
  workflow secrets and pass `--allow-token-auth` if your policies
  block silent token fallback.
- `buildx` is required so `--push` writes to all three registries
  in one build.
- For multi-arch, add `--platform linux/amd64,linux/arm64` via the
  target's extras (the DockerPushMixin honors `platforms`).
