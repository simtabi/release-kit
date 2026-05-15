# npm via GitLab Package Registry

**Automation level**: API
**Source-of-truth**: `package.json` `"version"`

## Overview

GitLab's npm registry is scoped per **project** (not per group by
default; group-level is paid). URL: `https://gitlab.com/api/v4/projects/<id>/packages/npm/`.

Useful when GitLab is your source-control host and you want npm
packages alongside the source. Less discoverable than npmjs.org;
use for **internal** packages.

## Account & project bootstrap

1. GitLab account exists.
2. Note your project's numeric ID (Project page → bottom-left
   "Project information" → "Project ID").
3. Scope name must match GitLab project's group: an account
   `simtabi` publishes `@simtabi/<pkg>`.

## Authentication options

1. **CI `CI_JOB_TOKEN`** — short-lived, scoped to the job. Preferred
   for CI.
2. **Deploy Token** with `read_package_registry` / `write_package_registry`.
3. **Project Access Token** with `api` scope (per-project, expirable).
4. **Personal Access Token** with `api` scope.

## One-time setup

### CI (GitLab CI)

```yaml
# bash / yaml
# .gitlab-ci.yml
publish-npm:
  stage: deploy
  image: node:20
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d/
  script:
    - |
      cat > .npmrc <<EOF
      @simtabi:registry=https://gitlab.com/api/v4/projects/${CI_PROJECT_ID}/packages/npm/
      //gitlab.com/api/v4/projects/${CI_PROJECT_ID}/packages/npm/:_authToken=${CI_JOB_TOKEN}
      EOF
    - npm publish
```

### Manual / local

```bash
# bash
# .npmrc (per-project, gitignored)
@simtabi:registry=https://gitlab.com/api/v4/projects/12345/packages/npm/
//gitlab.com/api/v4/projects/12345/packages/npm/:_authToken=glpat-YOUR-TOKEN-HERE
```

## Per-release workflow

### Manual

```bash
# bash
$EDITOR package.json              # bump version
npm publish
```

### CI/CD

Triggered by tag push per the rules block above. `CI_JOB_TOKEN` is
injected by GitLab.

## Verification

```bash
# bash
# 1. Web UI: Project → Deploy → Package Registry

# 2. Install (consumer)
# Consumer's .npmrc:
#   @simtabi:registry=https://gitlab.com/api/v4/projects/12345/packages/npm/
#   //gitlab.com/api/v4/projects/12345/packages/npm/:_authToken=<consumer-token>
npm install @simtabi/release-kit@1.4.2
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `404 - project not found` | Wrong numeric project ID | Look up under Project info |
| `401 - invalid_token` | Token missing `read_package_registry` for install or `write_package_registry` for publish | Regenerate with right scope |
| `409 - package_already_exists` | Re-publish same version | Bump |
| Scope mismatch between `package.json::name` and registry URL | GitLab enforces scope = group | Match `@<group-or-user>/<pkg>` |
| Slow upload (>30s for small package) | GitLab Pages cache / wrong region | Use the EU mirror if available |

## Security checklist

- [ ] CI uses `CI_JOB_TOKEN`, not a long-lived PAT.
- [ ] Deploy tokens (if used) are pinned to read-only for consumers,
      write-only for publishers — never both.
- [ ] `.npmrc` template doesn't carry a literal token in commits.
- [ ] Visibility of the package registry matches the project's
      visibility (private project → private registry by default).

## See also

- [`npm.md`](npm.md), [`npm-github.md`](npm-github.md) — other npm hosts
- [GitLab npm registry docs](https://docs.gitlab.com/ee/user/packages/npm_registry/)
