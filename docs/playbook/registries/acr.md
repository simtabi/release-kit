# Azure Container Registry (ACR)

**Automation level**: CLI login + API
**Source-of-truth**: `Dockerfile`

## Overview

Azure Container Registry stores OCI / Docker / Helm artifacts.
Per-registry naming; image reference:
`<registry-name>.azurecr.io/<repo>:<tag>`.

Tiers: Basic (10 GB), Standard (100 GB + geo-replication on
Premium), Premium (private endpoints, content trust, tasks).

## Account & project bootstrap

```bash
# bash
# Resource group
az group create -n my-rg -l eastus

# Registry
az acr create -n simtabireleasekit -g my-rg --sku Standard --location eastus

# Confirm
az acr show -n simtabireleasekit --query loginServer -o tsv
# -> simtabireleasekit.azurecr.io
```

Registry name is globally unique (DNS-style); 5-50 chars,
alphanumeric.

## Authentication options (ranked: most secure → least)

1. **Workload Identity / OIDC federation** from GitHub Actions /
   GitLab CI — no SP secret stored.
2. **Service Principal with Federated Credential** — short-lived
   token via `azure/login@v2`.
3. **Managed Identity** — for Azure VMs / AKS pods that push to
   ACR. No credential at all.
4. **Service Principal with client secret** — long-lived. 90-day
   rotation.
5. **Admin user** (`az acr update -n <name> --admin-enabled true`)
   — discouraged; account-wide root creds.

## One-time setup

### OIDC federation (GitHub Actions)

```bash
# bash
# 1. Create SP
APP_ID=$(az ad app create --display-name release-kit-pusher --query appId -o tsv)
SP_OBJECT_ID=$(az ad sp create --id $APP_ID --query id -o tsv)

# 2. Grant AcrPush on the registry
ACR_ID=$(az acr show -n simtabireleasekit --query id -o tsv)
az role assignment create --assignee $APP_ID --role AcrPush --scope $ACR_ID

# 3. Federated credential for the workflow
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-release-kit",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:simtabi/release-kit:ref:refs/tags/v*",
  "audiences": ["api://AzureADTokenExchange"]
}'

echo "Client ID: $APP_ID"
echo "Tenant ID: $(az account show --query tenantId -o tsv)"
echo "Subscription ID: $(az account show --query id -o tsv)"
```

### GitHub Actions workflow

```yaml
# bash / yaml
publish-acr:
  runs-on: ubuntu-latest
  permissions:
    id-token: write
    contents: read
  steps:
    - uses: actions/checkout@v4
    - uses: azure/login@v2
      with:
        client-id: ${{ vars.AZURE_CLIENT_ID }}
        tenant-id: ${{ vars.AZURE_TENANT_ID }}
        subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
    - run: az acr login --name simtabireleasekit
    - uses: docker/setup-buildx-action@v3
    - uses: docker/build-push-action@v6
      with:
        push: true
        platforms: linux/amd64,linux/arm64
        tags: simtabireleasekit.azurecr.io/release-kit:${{ github.ref_name }}
```

### Manual / local

```bash
# bash
az login
az acr login --name simtabireleasekit
```

## Per-release workflow

### Manual

```bash
# bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag simtabireleasekit.azurecr.io/release-kit:1.4.2 \
  --push .
```

### CI/CD

See OIDC workflow above.

## Verification

```bash
# bash
az acr repository show -n simtabireleasekit --image release-kit:1.4.2
docker pull simtabireleasekit.azurecr.io/release-kit:1.4.2
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `unauthorized: authentication required` | `az acr login` not run or token expired | Re-run; tokens expire after 3 hours |
| `forbidden: insufficient_scope` | Role assignment missing | Confirm `AcrPush` on the registry scope |
| `denied: requested access to the resource is denied` | Repo doesn't exist + content trust on | Pre-create the repo via `az acr repository create` |
| `Federated credential not found` | Subject claim mismatch | Inspect with `az ad app federated-credential list --id $APP_ID`; match exactly |
| Slow pulls in another region | No geo-replication (Basic/Standard tier) | Upgrade to Premium for geo-replication |

## Security checklist

- [ ] OIDC federation, not SP secret.
- [ ] Admin user disabled (`az acr update -n <name> --admin-enabled false`).
- [ ] Soft-delete enabled for tags
      (`az acr config soft-delete update --enabled true`).
- [ ] Quarantine + content trust on Premium SKU.
- [ ] Private endpoint configured if pulls must stay on Azure backbone.
- [ ] Image scanning via Defender for Cloud (paid).

## See also

- [`../cross-cutting/token-scoping.md::Azure Container Registry`](../cross-cutting/token-scoping.md)
- [`dockerhub.md`](dockerhub.md), [`gar.md`](gar.md), [`aws-ecr.md`](aws-ecr.md), [`ghcr.md`](ghcr.md)
- [ACR docs](https://learn.microsoft.com/azure/container-registry/)
