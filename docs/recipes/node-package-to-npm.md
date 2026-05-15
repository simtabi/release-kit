# Node package → npm + GHCR + GitHub Releases

TypeScript library + a Docker companion image, OIDC where possible.

## `release.json`

```json
{
  "project": {
    "name": "@my-org/my-package",
    "version_source": "package.json"
  },
  "targets": {
    "npm": {
      "enabled": true,
      "auth": "oidc",
      "package": "@my-org/my-package",
      "access": "public",
      "provenance": true
    },
    "ghcr": {
      "enabled": true,
      "auth": "oidc",
      "image": "ghcr.io/my-org/my-package",
      "tags": ["1.4.0", "latest"]
    },
    "github": {
      "enabled": true,
      "auth": "token",
      "repo": "my-org/my-package",
      "tag": "v1.4.0",
      "generate_notes": true
    }
  },
  "policies": {
    "default_dry_run": true,
    "require_changelog": true
  }
}
```

## Workflow

```yaml
name: release
on: { push: { tags: ["v*"] } }
permissions:
  id-token: write
  contents: write
  packages: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22", registry-url: "https://registry.npmjs.org" }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: npm ci && npm run build
      - run: pip install simtabi-release-kit
      - run: release-kit publish --apply
```

## One-time setup

1. npm: configure trusted publisher per
   <https://docs.npmjs.com/trusted-publishers>.
2. GHCR: nothing — the workflow's `GITHUB_TOKEN` with
   `packages: write` is enough.
3. `package.json` needs `"publishConfig": { "access": "public",
   "provenance": true }`.
