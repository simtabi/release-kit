# GitHub Enterprise Server (GHES)

**Automation level**: API (OIDC requires GHES 3.10+)
**Source-of-truth**: same as `github.md`

## Overview

GHES is the self-hosted GitHub appliance (AWS EC2 / GCP VM /
on-prem). Same REST + GraphQL APIs as github.com but on a
per-instance hostname (`github.example.com`).

Read [github.md](github.md) first; this page covers only the deltas.

## Account & project bootstrap

1. Your admin gives you the GHES hostname + your account credentials.
2. Authenticate `gh` against the GHES host:

```bash
# bash
gh auth login --hostname github.example.com
```

3. All subsequent `gh` and `gh api` calls now use that host.

## Authentication options

Order is the same as github.md, but **OIDC support depends on GHES
version**:

- GHES ≥ 3.10: OIDC issuer at
  `https://github.example.com/_services/token`. Workload identity
  federation to AWS / GCP / Azure works.
- GHES ≤ 3.9: no OIDC. Long-lived tokens only.

Confirm version with:

```bash
# bash
curl -fsSL https://github.example.com/api/v3/meta | jq .installed_version
```

## One-time setup

### Pointing `gh` and Actions at the host

```bash
# bash
# Local
export GH_HOST=github.example.com
gh repo list

# In Actions on GHES, the workflow runs natively against the host.
# Cross-instance Actions (running on github.com against GHES) need:
#   env:
#     GH_HOST: github.example.com
#     GH_TOKEN: ${{ secrets.GHES_TOKEN }}
```

### OIDC trust policy (GHES 3.10+)

GHES exposes the JWKS at:
`https://github.example.com/_services/token/.well-known/openid-configuration`

For an AWS IAM trust policy:

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::<acct>:oidc-provider/github.example.com/_services/token" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringLike": {
      "github.example.com/_services/token:sub": "repo:my-org/release-kit:*"
    }
  }
}
```

## Per-release workflow

Identical to `github.md`, with the GHES host substituted everywhere
`github.com` would appear.

## Verification

```bash
# bash
gh --hostname github.example.com release view v1.4.2
curl -fsSL "https://github.example.com/api/v3/repos/my-org/release-kit/releases/tags/v1.4.2"
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `gh auth login` lands on github.com | `--hostname` flag missed | Re-run with `--hostname github.example.com` |
| OIDC token rejected by consumer | GHES < 3.10 OR issuer URL mismatch | Upgrade GHES or fall back to PAT |
| Long pulls / pushes | Self-hosted runner network path | Run runners inside the same VPC as GHES |
| Actions don't start | Self-hosted runners offline | Admin: check `Settings → Actions → Runners` on the appliance |
| `gh api` 404 on org endpoint | API path is `/api/v3/...` on GHES (vs. `/` on github.com) | `gh` handles this when `GH_HOST` is set; raw `curl` needs the `/api/v3/` prefix |

## Security checklist

- [ ] All checklist items from `github.md`.
- [ ] GHES on a current major version (security patches).
- [ ] OIDC issuer URL (if supported) confirmed via JWKS endpoint.
- [ ] Runner SBOMs reviewed; self-hosted runners are most-privileged.
- [ ] Admin access to GHES via SSO + hardware key.
- [ ] LDAP / SAML sync confirmed for membership churn.

## See also

- [`github.md`](github.md) — base reference.
- [GHES admin docs](https://docs.github.com/en/enterprise-server)
- [GHES OIDC documentation](https://docs.github.com/en/enterprise-server/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
