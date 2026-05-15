# First publish

Going from clean clone to a published v0.1.0 in roughly an hour.

## 0. Prerequisites

- Git repo on `main`, working tree clean.
- A version source the tooling can read (`pyproject.toml`,
  `package.json`, `Cargo.toml`, `pom.xml`, or git tag).
- `pip install simtabi-release-kit`.

## 1. Scaffold

```bash
release-kit init
```

This writes `release.json` and `.env-example` to the current
directory and appends `.env` to `.gitignore`.

## 2. Edit `release.json`

Set the project name and add the targets you want. A minimal
example for a Python package going to PyPI + GHCR + GitHub
Releases:

```json
{
  "project": {
    "name": "my-package",
    "version_source": "pyproject.toml"
  },
  "targets": {
    "pypi":  { "enabled": true, "auth": "oidc", "package": "my-package" },
    "ghcr":  { "enabled": true, "auth": "oidc", "image": "ghcr.io/my-org/my-package", "tags": ["0.1.0", "latest"] },
    "github": { "enabled": true, "auth": "token", "repo": "my-org/my-package", "tag": "v0.1.0", "topics": ["python"] }
  },
  "policies": {
    "require_clean_git": true,
    "require_tag_match": true,
    "default_dry_run": true
  }
}
```

## 3. One-time bootstrap (manual, once per registry)

- **PyPI**: register the project name and add a trusted publisher
  pointing at your GitHub repo + workflow file.
  See [`playbook/registries/pypi.md`](../playbook/registries/pypi.md).
- **GHCR**: nothing to do; the GHCR token from the workflow's
  `GITHUB_TOKEN` is enough.
- **GitHub releases**: create a fine-grained PAT scoped to the
  repo with `Contents: Write`; export as `GITHUB_TOKEN` locally or
  store via `release-kit rotate-tokens --platform github`.

## 4. Local doctor

```bash
release-kit doctor
```

Every target should show GREEN. AMBER is acceptable for warnings
(e.g. a topics list left empty). RED blocks the publish.

## 5. Tag

```bash
git tag v0.1.0
git push origin v0.1.0
```

## 6. Dry-run

```bash
release-kit publish
```

Read the report. Every step should be `dry-run` (cyan).

## 7. Apply

```bash
release-kit publish --apply
```

For real. The report turns green; new versions appear on the
registries; the GitHub Release object is created.

## 8. Verify

```bash
release-kit publish --apply | tee publish.log
release-kit doctor   # quick re-check; tag URL is now live
```

For Python:

```bash
pipx run --pip-args="--no-cache-dir" my-package==0.1.0 --version
```

## 9. Wire CI for next time

See [`ci-release.md`](ci-release.md).
