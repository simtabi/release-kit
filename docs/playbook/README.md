# Release playbook

A reference playbook for publishing software to every major package
registry and git platform. Each page follows an identical template so
you can scan a section, find the same heading, and copy a working
command set.

The companion automation package, `simtabi-release-kit`, implements
most of these flows. The playbook is independent and stands alone as
a reference.

## How to use

1. Find your target (registry or git host) in the directory below.
2. Read the **Overview** and **Authentication options** to choose
   the right auth path (OIDC > short-lived token > long-lived token >
   username/password).
3. Run the **One-time setup**.
4. Wire up either the **Manual** or **CI/CD** flow under
   **Per-release workflow**.
5. Reference the **Verification** and **Common failure modes**
   sections when something is off.

## Per-platform template

Every platform page has these sections, in this order:

1. Overview
2. Account & project bootstrap
3. Authentication options (ranked: most secure → least)
4. One-time setup
5. Per-release workflow (manual + CI/CD)
6. Verification
7. Common failure modes & fixes
8. Security checklist

Pages cross-link to shared content rather than duplicating it. The
cross-cutting reference is in [`cross-cutting/`](cross-cutting/).

## Directory

### Registries

| Slug | Page | Automation |
|---|---|---|
| pypi | [registries/pypi.md](registries/pypi.md) | OIDC + API |
| npm | [registries/npm.md](registries/npm.md) | OIDC + API |
| npm-github | [registries/npm-github.md](registries/npm-github.md) | API |
| npm-gitlab | [registries/npm-gitlab.md](registries/npm-gitlab.md) | API |
| dockerhub | [registries/dockerhub.md](registries/dockerhub.md) | API |
| ghcr | [registries/ghcr.md](registries/ghcr.md) | OIDC + API |
| gitlab-registry | [registries/gitlab-registry.md](registries/gitlab-registry.md) | API |
| aws-ecr | [registries/aws-ecr.md](registries/aws-ecr.md) | CLI login + API |
| gar | [registries/gar.md](registries/gar.md) | CLI login + API |
| acr | [registries/acr.md](registries/acr.md) | CLI login + API |
| homebrew | [registries/homebrew.md](registries/homebrew.md) | PR-based |
| maven-central | [registries/maven-central.md](registries/maven-central.md) | API |
| rubygems | [registries/rubygems.md](registries/rubygems.md) | API |
| cargo | [registries/cargo.md](registries/cargo.md) | API |
| nuget | [registries/nuget.md](registries/nuget.md) | API |
| packagist | [registries/packagist.md](registries/packagist.md) | API |
| conda-forge | [registries/conda-forge.md](registries/conda-forge.md) | PR-based (backlog) |

### Git hosts

| Slug | Page | Automation |
|---|---|---|
| github | [git-hosts/github.md](git-hosts/github.md) | OIDC + API |
| github-enterprise-cloud | [git-hosts/github-enterprise-cloud.md](git-hosts/github-enterprise-cloud.md) | OIDC + API |
| github-enterprise-server | [git-hosts/github-enterprise-server.md](git-hosts/github-enterprise-server.md) | API (OIDC ≥ 3.10) |
| gitlab | [git-hosts/gitlab.md](git-hosts/gitlab.md) | OIDC + API |
| gitlab-self-managed | [git-hosts/gitlab-self-managed.md](git-hosts/gitlab-self-managed.md) | OIDC + API |
| bitbucket | [git-hosts/bitbucket.md](git-hosts/bitbucket.md) | API |
| bitbucket-dc | [git-hosts/bitbucket-dc.md](git-hosts/bitbucket-dc.md) | API |
| gitea | [git-hosts/gitea.md](git-hosts/gitea.md) | API (covers Forgejo) |
| azure-devops | [git-hosts/azure-devops.md](git-hosts/azure-devops.md) | API |

### Cross-cutting reference

| Topic | Page |
|---|---|
| OIDC trusted publishing matrix | [cross-cutting/oidc-matrix.md](cross-cutting/oidc-matrix.md) |
| Token scoping reference | [cross-cutting/token-scoping.md](cross-cutting/token-scoping.md) |
| Secret storage | [cross-cutting/secrets.md](cross-cutting/secrets.md) |
| Release versioning | [cross-cutting/versioning.md](cross-cutting/versioning.md) |
| Provenance & signing | [cross-cutting/provenance.md](cross-cutting/provenance.md) |
| Pre-flight checklist | [cross-cutting/preflight.md](cross-cutting/preflight.md) |

## Automation levels

Every page declares the platform's automation level at the top.

| Level | What it means |
|---|---|
| **OIDC + API** | Passwordless via CI OIDC; full API for everything else |
| **API** | Long-lived token + full HTTP/CLI automation |
| **CLI login + API** | One-time interactive `<tool> login`, then API |
| **PR-based** | Automation opens a PR; merge is human-gated |
| **Manual only** | No machine path; web UI required |

The CLI `release-kit doctor` reads these from each platform module
and renders a colour-coded readiness table.

## Style + conventions

- Shell blocks are annotated with the assumed shell: `bash` (default
  on macOS / Linux), `zsh` (interactive on modern macOS), `pwsh`
  (PowerShell 7+, default on Windows).
- Secrets are always placeholders shaped like
  `pypi-YOUR-TOKEN-HERE`, never realistic values.
- Cross-references use relative paths that resolve on GitHub.
- No platform page repeats content from `cross-cutting/`; it links.
