# OIDC trusted publishing matrix

Which registry trusts which CI provider's OIDC issuer, as of 2026.
OIDC removes long-lived secrets entirely: your CI job presents a
signed token, the registry verifies the signature + claims, and
publishes.

## Reading the matrix

`✅` means production-grade support, documented by the registry.
`🧪` means experimental / preview / behind a flag.
`❌` means no native support today (you need an API token).

## Matrix

| Registry | GitHub Actions | GitLab CI | Bitbucket Pipelines | CircleCI | Buildkite | Google Cloud Build |
|---|---|---|---|---|---|---|
| PyPI | ✅ | ✅ | ❌ | ❌ | ❌ | 🧪 |
| npm | ✅ (provenance) | ❌ | ❌ | ❌ | ❌ | ❌ |
| Docker Hub | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GHCR | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GitLab Container Registry | ❌ | ✅ (CI_JOB_TOKEN) | ❌ | ❌ | ❌ | ❌ |
| AWS ECR | ✅ (via `aws-actions/configure-aws-credentials`) | ✅ (web identity) | ✅ | ✅ | ✅ | ✅ |
| Google Artifact Registry | ✅ (via `google-github-actions/auth`) | ✅ (Workload Identity) | ✅ | ✅ | ✅ | ✅ |
| Azure Container Registry | ✅ (via `azure/login`) | ✅ (OIDC federation) | ❌ | ❌ | ❌ | ❌ |
| Maven Central (Sonatype) | 🧪 (Central Portal pilot) | ❌ | ❌ | ❌ | ❌ | ❌ |
| RubyGems | ✅ (since Mar 2024) | ❌ | ❌ | ❌ | ❌ | ❌ |
| crates.io | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| NuGet.org | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Packagist | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

## How OIDC works in one paragraph

The CI provider issues a JSON Web Token signed by its own well-known
OIDC issuer (e.g., `token.actions.githubusercontent.com`). The token
carries claims about the workflow: repository, branch / tag, actor,
environment. The registry has a stored "trust" policy: "I trust
tokens from this issuer where the `repository` claim is
`simtabi/release-kit` and the `environment` claim is `pypi`". On
match, the registry mints a short-lived publish token (or accepts
the OIDC token directly). No long-lived secret is involved.

## Issuer identifiers

| CI provider | Issuer URL |
|---|---|
| GitHub Actions | `https://token.actions.githubusercontent.com` |
| GitLab CI | `https://gitlab.com` (or your self-managed URL) |
| Bitbucket Pipelines | `https://api.bitbucket.org/2.0/workspaces/<workspace>/pipelines-config/identity/oidc` |
| CircleCI | `https://oidc.circleci.com/org/<org-id>` |
| Buildkite | `https://agent.buildkite.com` |

## Common OIDC claims used by registries

- `iss` — issuer URL (always)
- `sub` — workflow-specific subject (e.g., `repo:owner/repo:ref:refs/tags/v1.2.3`)
- `repository` — owner/repo (GitHub Actions)
- `repository_owner` — organisation slug
- `ref` — branch or tag ref
- `environment` — GitHub Environments name (recommended for binding)
- `aud` — audience the token is intended for; PyPI uses
  `pypi`, Docker Hub uses `https://hub.docker.com/`

The registry's trust policy binds these claims to a specific
publishing scope.

## When OIDC isn't available

Fall back to a **scoped, short-lived** API token from the registry,
stored as a CI secret. See
[`token-scoping.md`](token-scoping.md) for minimum permissions
per platform and
[`secrets.md`](secrets.md) for storage options.

## See also

- [Per-platform OIDC setup pages](../registries/) — each registry's
  page documents the exact CI configuration required.
- [`provenance.md`](provenance.md) — OIDC unlocks provenance
  attestations (Sigstore, SLSA).
