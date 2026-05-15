# GitHub Enterprise Cloud (GHEC)

**Automation level**: OIDC + API
**Source-of-truth**: same as `github.com` ([github.md](github.md))

## Overview

GHEC is the SaaS GitHub for enterprises. Same API surface and
hostname as `github.com` — `api.github.com`, `token.actions.githubusercontent.com`
for OIDC. Differences from `github.com`:

- **SAML SSO** enforced at the enterprise tenant level.
- **Audit log streaming** to Splunk / S3 / Azure Event Hubs.
- **IP allow-listing** at the enterprise level.
- **EMU** (Enterprise Managed User) accounts replace personal
  accounts for org members.

Read [github.md](github.md) first; this page covers only the deltas.

## Account & project bootstrap

1. Have an enterprise tenant invitation from your GitHub admin.
2. Authenticate `gh`: `gh auth login` → pick GitHub.com (yes, same
   host) → log in via SSO redirect.
3. For EMU tenants, your user handle is `<user>_<enterprise>`.
4. Create repos under your enterprise's org:

```bash
# bash
gh repo create my-enterprise-org/release-kit --internal \
  --description "Multi-registry publishing automation" \
  --license MIT --source=. --remote=origin --push
```

`--internal` makes the repo visible to all enterprise members but
not to the public.

## Authentication options

Same ranking as github.md, with one addition:

1. **OIDC ID-token** (preferred — same flow as github.com).
2. **Workflow `GITHUB_TOKEN`**.
3. **Fine-grained PAT** — requires SSO authorisation if the
   enterprise enforces SAML (gear icon on the PAT page → "Enable
   SSO" → authorise per org).
4. **Classic PAT** — same SSO requirement.

## One-time setup

Identical to `github.md` for repo settings, branch protection,
environments.

### SSO authorisation for tokens

PATs that interact with SAML-protected orgs need explicit
authorisation:

```bash
# bash
# After creating a PAT
gh api /user/emails    # this call may 401 with "Resource not accessible by integration"
                       # until the PAT is SSO-authorized
```

Authorize at:
`https://github.com/settings/tokens` → token → **Configure SSO** →
authorize per org.

### Audit log streaming

Configured at enterprise settings (admin role required); not
relevant to per-repo automation but worth confirming exists before
production publishing.

## Per-release workflow

Identical to `github.md`.

## Verification

Same `gh release view`, `gh api`, etc. Confirm the token is SSO-
authorized for any cross-org operation:

```bash
# bash
gh api /orgs/my-enterprise-org/repos | jq '.[0].name'
# 401 means token needs SSO authorization
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Resource protected by organization SAML enforcement` | Token not SSO-authorized | Settings → Tokens → Configure SSO |
| `Forbidden: not eligible for IP allow list` | Enterprise IP allow-list blocks the runner | Add the GitHub Actions hosted-runner IP ranges to the allow-list, or use self-hosted runners |
| `EMU user not allowed to push to public repo` | EMU accounts can't interact with non-enterprise repos | Use a personal account for public OSS contributions |

## Security checklist

- [ ] All checklist items from `github.md`.
- [ ] PATs SSO-authorised for the org.
- [ ] Enterprise audit log streaming verified.
- [ ] IP allow-list excludes hosted runners unless explicitly
      permitted.
- [ ] EMU policies match the org's compliance posture.

## See also

- [`github.md`](github.md) — base reference; this page is deltas
  only.
- [GHEC docs](https://docs.github.com/en/enterprise-cloud@latest)
