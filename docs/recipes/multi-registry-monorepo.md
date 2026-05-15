# Monorepo → distinct artifacts

One repo, multiple packages going to different registries. The
trick: one `release.json` per package, plus a matrix job in CI.

## Layout

```text
my-monorepo/
├── packages/
│   ├── core/        Python lib → PyPI
│   │   └── release.json
│   ├── cli/         Python app → PyPI + Docker Hub
│   │   └── release.json
│   └── web-sdk/     TypeScript lib → npm
│       └── release.json
└── .github/workflows/release.yml
```

## Per-package `release.json` (example: `packages/cli/release.json`)

```json
{
  "project": {
    "name": "my-cli",
    "version_source": "pyproject.toml"
  },
  "targets": {
    "pypi":     { "enabled": true, "auth": "oidc", "package": "my-cli" },
    "dockerhub": {
      "enabled": true, "auth": "token",
      "username": "my-org", "image": "my-org/my-cli",
      "tags": ["latest"]
    }
  }
}
```

## Matrix workflow

`.github/workflows/release.yml`:

```yaml
name: release
on:
  push:
    tags: ["*-v*"]   # tags like "cli-v1.4.0"

permissions:
  id-token: write
  contents: write

jobs:
  release:
    strategy:
      matrix:
        package: [core, cli, web-sdk]
      fail-fast: false
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: packages/${{ matrix.package }} } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install simtabi-release-kit
      - run: release-kit publish --apply
```

Tag form `cli-v1.4.0` lets you release one package at a time;
matrix entries that don't match the tag's prefix exit cleanly
when their `release.json` says the tag doesn't match the version
source.

## Gotchas

- **`fail-fast: false`** so one bad package doesn't kill the others.
- Each `release.json` lives next to its `pyproject.toml` /
  `package.json` so `version_source` resolves locally.
- The doctor sweep is per-package; run it inside each subdir during
  local development.
