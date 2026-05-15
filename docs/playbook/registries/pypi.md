# PyPI

**Automation level**: OIDC + API
**Source-of-truth for project metadata**: `pyproject.toml`

## Overview

The Python Package Index (`pypi.org`) is the canonical registry for
Python distributions. Publishes `.tar.gz` source distributions and
`.whl` wheels. Free, unauthenticated read access; authenticated
writes per project.

Test the same flow against `test.pypi.org` (a separate registry
with the same API).

## Account & project bootstrap

1. Create an account at `https://pypi.org/account/register/`.
2. Enable 2FA at `Account settings → Add 2FA with authentication
   application` (required for publishers since 2024).
3. Reserve the project name with the **first upload** (PyPI has no
   "claim a name" step; first valid sdist wins).
4. After first upload, add additional maintainers under
   `Manage project → Collaborators`.

## Authentication options (ranked: most secure → least)

1. **OIDC trusted publisher (recommended)** — no token stored.
   GitHub Actions / GitLab CI / Google Cloud Build.
2. **Per-project API token** — token starts with `pypi-`, scoped
   to a single project. Generated under
   `Account settings → API tokens → Add API token → Scope to project`.
3. **Entire-account API token** — same shape, broader blast radius.
   Use only for the one-time bootstrap upload that creates the
   project page; downgrade immediately after.
4. **Username + password** — deprecated for upload. Won't work
   with 2FA enabled.

## One-time setup

### OIDC trusted publisher (GitHub Actions)

PyPI side:
1. Go to your project's page → **Manage → Publishing**.
2. **Add a new publisher** under "Trusted publishers":
   - Owner: `simtabi` (your GitHub org)
   - Repository name: `release-kit` (your repo)
   - Workflow filename: `release.yml`
   - Environment name: `pypi` (recommended; gives you an
     Environments-protected secret store)
3. Click **Add**.

GitHub side:
1. Repo → **Settings → Environments → New environment** → name
   `pypi`. Add "Required reviewers" if you want a human gate.
2. Add `.github/workflows/release.yml`:

```yaml
# bash / yaml
name: release
on:
  push:
    tags: ['v*']

jobs:
  pypi-publish:
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/simtabi-release-kit
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.13' }
      - run: pip install --upgrade build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
        # No `with: password:` -- OIDC handles it
```

### Per-project API token (fallback)

1. Account settings → API tokens → **Add API token** → name
   `release-kit-publish` → **Scope to project** → pick the project.
2. Copy the `pypi-YOUR-TOKEN-HERE` value.
3. Store per [`../cross-cutting/secrets.md`](../cross-cutting/secrets.md).

## Per-release workflow

### Manual

```bash
# bash
# 1. Bump version + CHANGELOG (see ../cross-cutting/versioning.md)
$EDITOR pyproject.toml CHANGELOG.md

# 2. Commit + tag
git add -u
git commit -m "release: v1.4.2"
git tag -a v1.4.2 -m "v1.4.2"

# 3. Build
python -m build
ls dist/                     # *-1.4.2.tar.gz, *-1.4.2-py3-none-any.whl

# 4. Sanity check
twine check dist/*

# 5. Upload
twine upload dist/*
# Username: __token__
# Password: pypi-YOUR-TOKEN-HERE
```

Or with `~/.pypirc`:
```ini
# bash
# ~/.pypirc -- chmod 600
[pypi]
  username = __token__
  password = pypi-YOUR-TOKEN-HERE
```

Then `twine upload dist/*` is non-interactive.

### CI/CD (GitHub Actions, OIDC)

See **One-time setup** above. The workflow triggers on `git push
origin v1.4.2`. No secret to manage.

### CI/CD (GitLab CI, OIDC)

```yaml
# bash / yaml -- .gitlab-ci.yml
publish-pypi:
  stage: deploy
  image: python:3.13-slim
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d/
  id_tokens:
    PYPI_ID_TOKEN:
      aud: pypi
  script:
    - pip install --upgrade build twine id
    - python -m build
    - PYPI_TOKEN=$(id token --audience pypi | jq -r .value)
    - twine upload -u __token__ -p "$PYPI_TOKEN" dist/*
```

PyPI side: configure the trusted publisher with the GitLab
identity (different form than GitHub).

## Verification

```bash
# bash
# 1. Project page exists + lists new version
curl -fsSL https://pypi.org/pypi/simtabi-release-kit/json | jq .info.version

# 2. Wheel installs from PyPI
pip install --no-cache-dir --upgrade simtabi-release-kit==1.4.2

# 3. Provenance attestation (PEP 740)
pip download --no-deps simtabi-release-kit
sigstore verify identity \
  --bundle <file>.sigstore \
  --cert-identity-regexp 'https://github.com/simtabi/release-kit/.+' \
  --cert-oidc-issuer 'https://token.actions.githubusercontent.com'
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `400 Bad Request: File already exists` | Re-upload of same version | Bump version; PyPI never lets you re-upload |
| `403 Forbidden: invalid token` | Token scoped to a different project | Use entire-account or per-project token for THIS project |
| `400 The user 'X' isn't allowed to upload to project 'Y'` | Account not a maintainer | Add the account under `Manage → Collaborators` |
| `Trusted publisher mismatch` | OIDC claims don't match policy | Check `repository`, `workflow_ref`, `environment` claims; PyPI logs the actual claims on failure |
| `400 Description must be UTF-8` | Long-description (README) has encoding issues | `python -c "open('README.md').read()"` — fix the file |
| `400 Filename invalid` | Non-PEP 427 wheel name | Rebuild with current `build`; wheel filename format is strict |
| Upload succeeds but `pip install` fails | CDN propagation lag | Wait 60-90 seconds; PyPI's Fastly cache catches up |

## Security checklist

- [ ] Token has expiry set (PyPI tokens don't auto-expire; rotate
      manually every 90 days).
- [ ] Token is per-project scoped after the bootstrap upload.
- [ ] OIDC trusted publisher is configured if you have GitHub
      Actions or GitLab CI.
- [ ] Provenance attestations enabled (PEP 740, `attestations: true`
      in the `pypa/gh-action-pypi-publish` action).
- [ ] CHANGELOG dated section for this version exists.
- [ ] `dist/` is rebuilt from a clean tree, not incrementally.
- [ ] No `.env`, `*.key`, `id_rsa*` in the wheel
      (`unzip -l dist/*.whl | grep -E '\.(env|key|pem|p12)$'`).
- [ ] 2FA enabled on the publishing account.

## See also

- [`../cross-cutting/oidc-matrix.md`](../cross-cutting/oidc-matrix.md)
  for the trusted-publisher matrix.
- [`../cross-cutting/token-scoping.md`](../cross-cutting/token-scoping.md)
  for the per-project vs. entire-account discussion.
- [`../cross-cutting/provenance.md`](../cross-cutting/provenance.md)
  for PEP 740 attestation details.
