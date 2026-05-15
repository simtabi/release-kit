# Secret storage

Where publish credentials live, ranked from "must never see the
disk" to "convenient for dev only". The release-kit token-resolution
chain checks these in order.

## Storage options, ranked

1. **CI provider's OIDC trusted publisher** — no secret stored
   anywhere. Best.
2. **CI provider secret store** with environment-binding — GitHub
   Environments, GitLab CI/CD Variables (protected, masked),
   Bitbucket Workspace Variables. The secret never leaves the
   provider's encrypted store.
3. **OS keyring** (laptop / workstation):
   - macOS: Keychain (`security` command)
   - Linux: Secret Service (`gnome-keyring`, `kwallet`,
     `keyring` Python lib)
   - Windows: Credential Manager
4. **Dedicated secret manager**:
   - HashiCorp Vault (KV v2 engine)
   - 1Password CLI (`op read op://Vault/Item/field`)
   - AWS Secrets Manager
   - GCP Secret Manager
   - Azure Key Vault
5. **`.env` file (gitignored)** — dev convenience only. Never in
   CI, never on a shared machine.
6. **Plain environment variable in shell history** — discouraged;
   use `read -s` or a tool that doesn't echo.
7. **Hard-coded in source** — never.

## release-kit resolution order

When release-kit needs a token, it tries these in order:

1. Explicit constructor / fluent-API parameter
2. Environment variable named in the JSON config (`auth.env_var`)
3. `.env` file in the project root (if `python-dotenv` resolves it)
4. OS keyring entry under the service name
   `release-kit:<platform-slug>`
5. **Fail** with a typed exception listing what to set next

`--allow-token-auth` is required on the CLI before release-kit
falls back from OIDC to any of the above. This prevents accidental
"OIDC misconfigured, silently used long-lived token" runs.

## GitHub Actions secrets

```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ['v*']

jobs:
  publish:
    runs-on: ubuntu-latest
    environment:
      name: pypi              # binds secrets to an Environment
    permissions:
      id-token: write         # for OIDC
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/gh-action-pypi-publish@release/v1
        # No `with: password:` -- OIDC handles it
```

Set Environments at **Repo Settings → Environments**. Add
"Required reviewers" to gate the deploy step on a human approval.

## GitLab CI/CD variables

```yaml
# .gitlab-ci.yml
publish-pypi:
  stage: deploy
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d/
  script:
    - python -m build
    - twine upload --username __token__ --password $PYPI_TOKEN dist/*
```

Set `PYPI_TOKEN` at **Settings → CI/CD → Variables**:
- Type: `Variable`
- **Protected**: ✅ (only protected refs / tags)
- **Masked**: ✅
- **Environment scope**: production (or your release scope)

OIDC alternative uses `id_tokens:` in the job and `CI_JOB_JWT_V2`:

```yaml
publish-pypi:
  id_tokens:
    PYPI_ID_TOKEN:
      aud: pypi
```

## Bitbucket Pipelines

Set at **Workspace settings → OpenID Connect** for OIDC; at
**Repository settings → Repository variables** for static
secrets. Mark `Secured` to mask in logs.

## HashiCorp Vault

```bash
# bash
export VAULT_ADDR=https://vault.example.com
vault login -method=oidc

# Read a publish token at runtime
PYPI_TOKEN=$(vault kv get -field=token secret/release/pypi)
twine upload -u __token__ -p "$PYPI_TOKEN" dist/*
```

For long-running CI, use the `vault-action` GitHub Action or
`vault read`/`vault kv get` in `.gitlab-ci.yml`'s `before_script`.

## 1Password CLI

```bash
# bash
op signin
PYPI_TOKEN=$(op read "op://Eng/PyPI/credential")
twine upload -u __token__ -p "$PYPI_TOKEN" dist/*
```

For CI, use the official Service Account: `OP_SERVICE_ACCOUNT_TOKEN`
env var unlocks read-only access to a designated vault.

## AWS Secrets Manager / SSM Parameter Store

```bash
# bash
PYPI_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id /release/pypi \
  --query SecretString --output text)
```

For ECR pushes, IAM is the credential — no separate secret to store.

## GCP Secret Manager

```bash
# bash
PYPI_TOKEN=$(gcloud secrets versions access latest \
  --secret=pypi-token --project=my-project)
```

Workload Identity Federation removes the GCP key entirely for
GitHub Actions / GitLab CI workloads.

## Azure Key Vault

```bash
# bash
PYPI_TOKEN=$(az keyvault secret show \
  --vault-name my-vault --name pypi-token \
  --query value -o tsv)
```

`azure/login@v2` with OIDC removes the SP secret.

## Local dev with .env

The release-kit ships a `.env-example` listing every supported
platform's env vars with commented placeholders. Copy to `.env`,
fill in dev tokens, and `.env` is gitignored by the package's
default `.gitignore`.

```bash
# bash
cp .env-example .env
chmod 600 .env
$EDITOR .env
```

Confirm `.env` is in `.gitignore` before committing anything:

```bash
# bash
grep -q '^\.env$' .gitignore || echo "MISSING: add .env to .gitignore"
```

## Rotation tooling

`release-kit rotate-tokens <platform>` walks an interactive
rotation:
1. Open the registry's token-management page in the user's browser.
2. Prompt for the new token.
3. Update the OS keyring entry.
4. Update the CI provider's secret via API (where supported).
5. Refresh `.env-example` documentation.

The old token is left active until the user confirms the new one
works (run `release-kit doctor` between steps).

## Audit cadence

| Action | Frequency |
|---|---|
| Review who has access to CI secrets | Quarterly |
| Rotate fine-grained PATs | 90 days |
| Rotate cloud IAM keys | 90 days |
| Rotate OS keyring stale entries (laptop replaced, employee left) | Immediately |
| Audit OIDC trust policies | When adding / removing repos |

## See also

- [`token-scoping.md`](token-scoping.md) — what permissions each
  token needs
- [`oidc-matrix.md`](oidc-matrix.md) — where OIDC removes the
  storage problem entirely
