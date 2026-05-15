# GitLab Self-Managed / Dedicated

**Automation level**: OIDC + API
**Source-of-truth**: same as [`gitlab.md`](gitlab.md)

## Overview

Self-Managed GitLab is the on-prem / self-hosted edition; Dedicated
is GitLab's single-tenant SaaS. Same REST API v4 as gitlab.com,
hostname-substituted. OIDC works out of the box.

Read [gitlab.md](gitlab.md) first; this page is deltas.

## Account & project bootstrap

1. Get the instance hostname + sign-in URL from your admin.
2. Authenticate `glab` against the instance:

```bash
# bash
glab auth login --hostname gitlab.example.com
```

3. Project creation, settings, CI: identical to gitlab.md, with
   `gitlab.com` replaced everywhere.

## Authentication options

Same ranking. Token formats are identical (`glpat-…`,
`gldt-…`, etc.).

## One-time setup

### OIDC trust policy

Self-managed GitLab's OIDC issuer:
`https://gitlab.example.com`. JWKS:
`https://gitlab.example.com/oauth/discovery/keys`.

For AWS IAM:

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::<acct>:oidc-provider/gitlab.example.com" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "gitlab.example.com:aud": "https://gitlab.example.com"
    },
    "StringLike": {
      "gitlab.example.com:sub": "project_path:my-group/release-kit:*"
    }
  }
}
```

### Repo settings, branch protection

Identical to gitlab.md; substitute the hostname in `glab` calls
or use `--hostname`.

## Per-release workflow

Identical to gitlab.md.

## Verification

```bash
# bash
glab --hostname gitlab.example.com release view v1.4.2
curl -fsSL "https://gitlab.example.com/api/v4/projects/<id>/releases/v1.4.2" \
  --header "PRIVATE-TOKEN: $GL_TOKEN"
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `glab` defaults to gitlab.com | `--hostname` missed | `glab auth login --hostname gitlab.example.com` first |
| OIDC issuer cert untrusted | Self-managed with private CA | Add the CA bundle to your CI runner OS trust store |
| Runner can't reach GitLab | Network policy / firewall | Runner must reach the instance over HTTPS; check egress |
| Long backups, slow API | Instance under-provisioned | Talk to the admin |

## Security checklist

- [ ] All checklist items from gitlab.md.
- [ ] Instance on a current major version (security patches).
- [ ] Database backups verified.
- [ ] Admin access restricted to a handful of named humans.
- [ ] `omniauth-saml` or LDAP integration aligned with company IdP.

## See also

- [`gitlab.md`](gitlab.md) — base reference.
- [GitLab admin docs](https://docs.gitlab.com/ee/administration/)
