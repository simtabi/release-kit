# Token scoping reference

Minimum permissions per operation per platform. Tokens issued
broader than this are an unnecessary blast radius; tokens scoped
narrower than this won't work.

## Reading the table

Each row pairs a publish operation with the minimum scope (or IAM
permission) the issuing token needs. Scopes that are
platform-specific (PyPI's per-project tokens, Google's IAM roles)
are explained in the **Notes** column.

## PyPI

| Operation | Minimum scope | Notes |
|---|---|---|
| First-ever upload (project does not exist) | Entire-account token | One-time bootstrap; downgrade after |
| Publish a new version | Per-project token | Generate from `Settings → API tokens → scope to project` |
| Read project metadata | None (public) | |
| Delete a release | Entire-account token | Discouraged; yank instead |

Prefer OIDC trusted publisher (no token at all). See
[`oidc-matrix.md`](oidc-matrix.md).

## npm

| Operation | Token type | Notes |
|---|---|---|
| Publish (CI) | **Automation token** | Bypasses 2FA OTP prompts; required for unattended publish |
| Publish (interactive) | Publish token | Triggers 2FA on `npm publish` |
| Read-only (CI install of private packages) | Read-only token | Or granular access token scoped to download |
| Provenance | OIDC (no token) | GitHub Actions only; see [`provenance.md`](provenance.md) |

## GitHub (PAT)

Use **fine-grained PATs** over classic PATs whenever possible.

| Operation | Fine-grained permission | Classic scope |
|---|---|---|
| Create release | Contents: Read & write | `repo` |
| Push to repo | Contents: Read & write | `repo` |
| Push to GHCR | Packages: Read & write | `write:packages` |
| Read GHCR | Packages: Read | `read:packages` |
| Manage repo settings | Administration: Read & write | `repo` |
| Add topics | Metadata: Read & write | `public_repo` |
| Branch protection | Administration: Read & write | `repo` |

## Docker Hub

| Operation | Access token permission |
|---|---|
| Push images to a namespace | **Read, Write, Delete** (per-namespace) |
| Pull only | Read |
| Manage tags | Read, Write |

Generated at `hub.docker.com → Account Settings → Personal access
tokens → New Access Token`. Per-namespace scoping is the
narrowest the platform supports.

## GHCR (GitHub Container Registry)

Same as GitHub PAT above:
- Push: `packages:write` (classic) or `Packages: Read & write`
  (fine-grained)
- Pull (public): no auth required
- Pull (private): `packages:read`

Prefer GitHub Actions `GITHUB_TOKEN` with workflow-level
`permissions: packages: write` over a long-lived PAT.

## AWS ECR

IAM policy (private ECR):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRPush",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:<region>:<account>:repository/<repo-name>"
    },
    {
      "Sid": "ECRGetAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    }
  ]
}
```

For Public ECR, replace `ecr:` with `ecr-public:` and use
`us-east-1` (the only region for Public ECR).

## Google Artifact Registry

IAM roles:

| Operation | Minimum role |
|---|---|
| Push images | `roles/artifactregistry.writer` |
| Pull images | `roles/artifactregistry.reader` |
| Manage repository | `roles/artifactregistry.repoAdmin` |

Bind on the **repository** level, not the project, to limit blast
radius.

## Azure Container Registry

Built-in roles:

| Operation | Role |
|---|---|
| Push | `AcrPush` |
| Pull | `AcrPull` |
| Manage | `AcrPush` + `AcrDelete` |

Or use a Service Principal with the `AcrPush` role scoped to the
registry resource.

## GitLab

Personal Access Token scopes:

| Operation | Scope |
|---|---|
| Push to repository | `write_repository` |
| Push to Container Registry | `write_registry` |
| Push to Packages (npm/maven/etc.) | `api` |
| Manage project | `api` |
| Trigger pipelines | `api` |

**Project Access Tokens** (per-project, expirable) preferred over
PATs for CI use. **Deploy Tokens** preferred for pull-only.

## Bitbucket Cloud

App passwords:

| Operation | Permission |
|---|---|
| Push to repository | `repository:write` |
| Create release | `repository:write` + `pipeline:write` |
| Read CI status | `repository:read` |

## Maven Central

| Operation | Credential |
|---|---|
| Deploy via Central Portal | Portal API token |
| Deploy via legacy OSSRH | Sonatype Jira account password |
| GPG sign | Local GPG key + passphrase (never in CI plaintext) |

## RubyGems

| Operation | Scope |
|---|---|
| Push gems | `push_rubygem` |
| Yank gems | `yank_rubygem` |
| Manage owners | `update_or_remove_owner` |

Per-gem scoping (since 2023): tokens can be scoped to specific gems
in the gem's settings page.

## crates.io

| Operation | Scope |
|---|---|
| Publish | `publish-new` (first time) + `publish-update` |
| Yank | `yank` |
| Manage owners | `change-owners` |

Set on token creation at `crates.io → Account Settings → API Tokens`.

## NuGet

| Operation | API key permission |
|---|---|
| Push packages | `Push` |
| Unlist packages | `Push` |
| Push new packages only | `Push new packages and package versions` |

Scope by glob pattern (`MyOrg.*`) to limit which package IDs the
key can publish.

## Packagist

| Operation | Token |
|---|---|
| Submit / update package | API token (account-level) + webhook receiver |
| Trigger refresh | API token |

Webhook from your git host (GitHub / GitLab / Bitbucket) triggers
the refresh automatically once the package is registered. No
per-version push step.

## Rotation cadence

Minimum guidance:

| Token kind | Rotate every |
|---|---|
| OIDC trust policy | When the source CI workflow's identity claims change |
| Fine-grained PAT | 90 days |
| Classic PAT | Avoid; if used, 30 days |
| Cloud IAM key (AWS access key, GCP SA key) | 90 days |
| Bot account password | 180 days |

See [`secrets.md`](secrets.md) for storage and rotation tooling.

## See also

- [`oidc-matrix.md`](oidc-matrix.md) — which registries support OIDC
- [`secrets.md`](secrets.md) — where to store these tokens
- Per-platform pages under [`../registries/`](../registries/) and
  [`../git-hosts/`](../git-hosts/) for exact UI navigation
