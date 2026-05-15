# Azure DevOps Repos

**Automation level**: API
**Source-of-truth**: organisation + project + repo settings

## Overview

Azure DevOps Repos (formerly TFS / VSTS) is Microsoft's enterprise
git host. URL pattern: `https://dev.azure.com/<org>/<project>/_git/<repo>`.

Sibling services in the Azure DevOps family: Pipelines (CI),
Boards (issues), Artifacts (packages), Test Plans. This page is
just Repos + Pipelines for releases.

REST API: `https://dev.azure.com/<org>/_apis/...?api-version=7.1`.
CLI: `az devops`.

## Account & project bootstrap

1. Create or use an existing Azure DevOps organisation (free for
   up to 5 users).
2. Install `az devops` extension:

```bash
# bash
az extension add --name azure-devops
az devops configure --defaults organization=https://dev.azure.com/<org> project=<project>
```

3. Create the repo:

```bash
# bash
az repos create --name release-kit \
  --project <project> --organization https://dev.azure.com/<org>
```

## Authentication options (ranked: most secure → least)

1. **Azure DevOps OIDC** (Service Connection → Workload Identity
   Federation) — for Pipelines federating to AWS, GCP, Azure.
2. **Personal Access Token (PAT)** with the minimum scopes for the
   operation. Per-user, expiring.
3. **Service Principal** (Azure AD) — for cross-org / cross-tenant.
4. **SSH key** — for git pushes only, not API.

## One-time setup

### Repo branch policies

Branch policies in Azure DevOps replace GitHub's "branch protection":

```bash
# bash
REPO_ID=$(az repos show --repository release-kit --query id -o tsv)

# Require minimum reviewers
az repos policy approver-count create \
  --repository-id $REPO_ID --branch main \
  --minimum-approver-count 1 --creator-vote-counts false \
  --allow-downvotes false --reset-on-source-push true \
  --blocking true --enabled true

# Require build to pass (after configuring a build pipeline)
az repos policy build create \
  --repository-id $REPO_ID --branch main \
  --build-definition-id <build-id> \
  --blocking true --enabled true
```

### PAT generation

UI: User settings (top-right) → **Personal access tokens →
New Token**:

- Name: `release-kit-publish`
- Scopes: Code (Read & write); Build (Read & execute); Release
  (Read, write & execute) — pick narrowest sufficient set
- Expiry: max 1 year

## Per-release workflow

### Manual

```bash
# bash
git push origin v1.4.2

# Create a release (tag-as-release model)
az repos ref create --name refs/tags/v1.4.2 \
  --object-id $(git rev-parse v1.4.2^{}) \
  --repository release-kit
```

Azure DevOps doesn't have a first-class "Release" object like
GitHub or GitLab; tags + artifact feeds carry the release semantics.

### CI/CD (Azure Pipelines, YAML)

```yaml
# bash / yaml
# azure-pipelines.yml
trigger:
  tags:
    include: ['v*']
pr: none

pool:
  vmImage: ubuntu-latest

steps:
  - task: UsePythonVersion@0
    inputs: { versionSpec: '3.13' }

  - script: |
      pip install build twine
      python -m build
    displayName: Build

  - task: TwineAuthenticate@1
    inputs:
      pythonUploadServiceConnection: 'pypi-service-connection'

  - script: twine upload -r pypi-service-connection dist/*
    displayName: Publish
```

## Verification

```bash
# bash
# Tag exists
az repos ref list --repository release-kit --filter refs/tags | jq '.[].name'

# Build / pipeline ran for the tag
az pipelines runs list --project <project> --branch refs/tags/v1.4.2
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `TF400898: An internal error occurred` | PAT scope insufficient | Regenerate with `Code (Read & write)` |
| `Resource not found` on REST call | Missing `api-version=7.1` query string | Add it to every call |
| Pipeline doesn't trigger on tag | Trigger missing `tags:` block | Add the YAML trigger config above |
| Service Connection unauthorized | Service principal lacks role assignment | Az portal → DevOps → Project Settings → Service Connections → Grant access |
| `az devops` command not found | Extension not installed | `az extension add --name azure-devops` |

## Security checklist

- [ ] MFA enabled on Azure AD account.
- [ ] PATs scoped narrowly; expire ≤ 1 year.
- [ ] Service Connections use Workload Identity Federation (not
      key).
- [ ] Branch policies on `main` (≥1 reviewer, blocking build,
      no merge-without-vote).
- [ ] Restricted "Allow contributors to bypass policies" off.
- [ ] Audit log streaming to Log Analytics.
- [ ] Inherit org-level security policies (Conditional Access).

## See also

- [Azure DevOps REST API](https://learn.microsoft.com/rest/api/azure/devops/)
- [Azure Pipelines YAML schema](https://learn.microsoft.com/azure/devops/pipelines/yaml-schema/)
- [`../registries/acr.md`](../registries/acr.md) — Azure Container
  Registry pairs naturally with Azure DevOps Pipelines
