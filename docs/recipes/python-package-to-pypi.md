# Python package → PyPI + GitHub Releases

The most common release-kit shape. Single Python package, OIDC
to PyPI, GitHub release object for changelog visibility.

## `release.json`

```json
{
  "$schema": "./schema/release-kit.schema.json",
  "project": {
    "name": "my-package",
    "version_source": "pyproject.toml"
  },
  "targets": {
    "pypi": {
      "enabled": true,
      "auth": "oidc",
      "package": "my-package"
    },
    "github": {
      "enabled": true,
      "auth": "token",
      "repo": "my-org/my-package",
      "tag": "v1.0.0",
      "generate_notes": true,
      "topics": ["python", "oss"]
    }
  },
  "policies": {
    "require_clean_git": true,
    "require_tag_match": true,
    "require_changelog": true,
    "default_dry_run": true
  }
}
```

## `.github/workflows/release.yml`

```yaml
name: release
on:
  push:
    tags: ["v*"]

permissions:
  id-token: write
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install build simtabi-release-kit
      - run: python -m build
      - run: release-kit doctor
      - run: release-kit publish --apply
```

## One-time setup

1. <https://pypi.org/manage/account/publishing/> → add trusted
   publisher for `my-org/my-package`, workflow `release.yml`,
   environment `pypi`.
2. Repo settings → Environments → create `pypi`; add required
   reviewers if you want a human in the loop.
3. Create a fine-grained PAT for `GITHUB_TOKEN` fallback (the
   built-in `GITHUB_TOKEN` is fine for releases, but rotate it via
   `release-kit rotate-tokens` if you'd rather use a long-lived
   one).

## Cut a release

```bash
# update version in pyproject.toml
git commit -am "release v1.0.0"
git tag v1.0.0
git push origin v1.0.0
```

The workflow fires, doctor goes green, publish dry-runs, then
applies, and the GitHub Release shows up with auto-generated
notes.
