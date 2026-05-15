# Google Artifact Registry (GAR)

**Automation level**: CLI login + API
**Source-of-truth**: `Dockerfile`

## Overview

GAR is Google Cloud's general-purpose package registry (OCI / Docker,
Maven, npm, PyPI, apt/yum). Single registry can host multiple formats.

Image reference: `<region>-docker.pkg.dev/<project>/<repo>/<image>:<tag>`.

## Account & project bootstrap

1. Have a GCP project (`gcloud projects create`).
2. Enable the API: `gcloud services enable artifactregistry.googleapis.com`.
3. Create a Docker repo:
   ```bash
   # bash
   gcloud artifacts repositories create my-repo \
     --repository-format=docker \
     --location=us-central1 \
     --description="Container images"
   ```
4. Note the registry hostname: `us-central1-docker.pkg.dev`.

## Authentication options (ranked: most secure → least)

1. **Workload Identity Federation (WIF)** — OIDC from GitHub Actions
   / GitLab CI / Bitbucket. No GCP key material.
2. **Service Account with short-lived token** — `gcloud auth
   print-access-token` on an SA.
3. **Service Account JSON key file** — long-lived. Rotate every
   90 days; treat like a password.
4. **User account `gcloud auth login`** — local dev only.

## One-time setup

### Workload Identity Federation (GitHub Actions)

```bash
# bash
# 1. Create the WIF pool + provider
gcloud iam workload-identity-pools create gh-pool \
  --location=global --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc gh-provider \
  --workload-identity-pool=gh-pool --location=global \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='simtabi/release-kit'"

# 2. Create the SA + grant push permission
gcloud iam service-accounts create release-kit-pusher

gcloud artifacts repositories add-iam-policy-binding my-repo \
  --location=us-central1 \
  --member="serviceAccount:release-kit-pusher@<project>.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# 3. Allow the WIF principal to impersonate the SA
gcloud iam service-accounts add-iam-policy-binding \
  release-kit-pusher@<project>.iam.gserviceaccount.com \
  --member="principalSet://iam.googleapis.com/projects/<num>/locations/global/workloadIdentityPools/gh-pool/attribute.repository/simtabi/release-kit" \
  --role="roles/iam.workloadIdentityUser"
```

### GitHub Actions workflow

```yaml
# bash / yaml
publish-gar:
  runs-on: ubuntu-latest
  permissions:
    id-token: write
    contents: read
  steps:
    - uses: actions/checkout@v4
    - uses: google-github-actions/auth@v2
      with:
        workload_identity_provider: projects/<num>/locations/global/workloadIdentityPools/gh-pool/providers/gh-provider
        service_account: release-kit-pusher@<project>.iam.gserviceaccount.com
    - run: gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
    - uses: docker/setup-buildx-action@v3
    - uses: docker/build-push-action@v6
      with:
        push: true
        platforms: linux/amd64,linux/arm64
        tags: |
          us-central1-docker.pkg.dev/<project>/my-repo/release-kit:${{ github.ref_name }}
          us-central1-docker.pkg.dev/<project>/my-repo/release-kit:latest
```

### Manual / local

```bash
# bash
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

## Per-release workflow

### Manual

```bash
# bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag us-central1-docker.pkg.dev/<project>/my-repo/release-kit:1.4.2 \
  --push .
```

### CI/CD

See WIF workflow above.

## Verification

```bash
# bash
gcloud artifacts docker images list us-central1-docker.pkg.dev/<project>/my-repo
docker pull us-central1-docker.pkg.dev/<project>/my-repo/release-kit:1.4.2
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `denied: Permission "artifactregistry.repositories.uploadArtifacts" denied` | SA missing role | `roles/artifactregistry.writer` on the repo |
| `unauthorized: failed authentication` | `gcloud auth configure-docker` not run | Run it; updates `~/.docker/config.json` |
| WIF auth fails: `workloadIdentityPools/.../subject is not a member` | Attribute condition wrong | Inspect the actual JWT claim with `id-token` output; match exactly |
| `Repository does not exist` | Wrong region or repo name | `gcloud artifacts repositories list --location=us-central1` |
| Slow first push from outside US | Cross-region transfer | Use a regional repo close to your build runners |

## Security checklist

- [ ] WIF used, no long-lived JSON keys.
- [ ] If JSON keys are used, they're rotated every 90 days and
      stored in a secret manager (not on disk).
- [ ] Repo IAM bindings are scoped to the specific repo, not the
      project.
- [ ] Vulnerability scanning enabled
      (`gcloud artifacts vulnerabilities`).
- [ ] Image-tag immutability: GAR supports tag re-write by default;
      use SHA refs in production for safety.
- [ ] CMEK (Customer-Managed Encryption Keys) if compliance demands.

## See also

- [`../cross-cutting/token-scoping.md::Google Artifact Registry`](../cross-cutting/token-scoping.md)
- [GAR docs](https://cloud.google.com/artifact-registry/docs)
