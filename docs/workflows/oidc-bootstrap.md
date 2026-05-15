# OIDC bootstrap

How to set up OIDC trusted publishing per registry. Once
configured, the CI workflow exchanges an ephemeral ID token at
publish time; no long-lived tokens sit in the secret store.

## Prereqs

- A CI runner that issues OIDC ID tokens (GitHub Actions, GitLab
  CI with `id_tokens`, CircleCI, Buildkite, etc.).
- A repo with a permission grant equivalent to GitHub Actions'
  `permissions: { id-token: write }`.

## PyPI

1. Log into <https://pypi.org/manage/account/publishing/>.
2. Add a new "trusted publisher" entry:
   - Owner: `my-org`
   - Repository: `my-package`
   - Workflow filename: `release.yml`
   - Environment: leave blank or use `pypi` if you've protected the
     environment in GitHub.
3. Save.

Workflow snippet:

```yaml
permissions:
  id-token: write
jobs:
  release:
    runs-on: ubuntu-latest
    environment: pypi   # optional but recommended
    steps:
      - run: release-kit publish --target pypi --apply
```

Full reference: [`playbook/registries/pypi.md`](../playbook/registries/pypi.md).

## npm

1. <https://docs.npmjs.com/trusted-publishers> walks the
   registry-side setup.
2. The package's `package.json` must include a `publishConfig`
   block with `provenance: true`.
3. Workflow needs `id-token: write` + Node 22+.

Workflow snippet:

```yaml
- run: npm publish --provenance --access public
```

…or via release-kit:

```yaml
- run: release-kit publish --target npm --apply
```

## GHCR

GHCR uses the workflow's `GITHUB_TOKEN`; no extra OIDC dance.
Workflow needs `packages: write`.

```yaml
permissions:
  packages: write
- run: release-kit publish --target ghcr --apply
```

## RubyGems

<https://guides.rubygems.org/trusted-publishing/> is the
authoritative guide. Set up a trusted publisher pointing at the
repo + workflow. Then:

```yaml
permissions:
  id-token: write
- run: release-kit publish --target rubygems --apply
```

## AWS ECR (via GitHub-OIDC)

1. Create an IAM identity provider for
   `token.actions.githubusercontent.com` in AWS.
2. Create an IAM role with `ecr:PutImage`, `ecr:BatchCheckLayer…`,
   `ecr:InitiateLayerUpload`, etc., trusted by the OIDC provider
   scoped to `repo:my-org/my-package:ref:refs/tags/v*`.
3. Workflow uses
   [`aws-actions/configure-aws-credentials`](https://github.com/aws-actions/configure-aws-credentials):

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/release-kit-pusher
    aws-region: us-east-1
- run: release-kit publish --target aws-ecr --apply
```

## Verifying OIDC is working

Run `release-kit doctor` from within the CI workflow itself; the
auth column will show `OIDC` for trusted-publish targets if the ID
token resolved. If it falls back to `TOKEN`, the workflow's
permissions are wrong.

A common failure: forgetting `id-token: write` at the **workflow**
level. Setting it on a single job is not enough if a step expects
the env var to be present earlier.

## Falling back without breaking

Set `policies.allow_token_auth = false` (the default) to refuse
silent fallback to a long-lived token when OIDC fails. Override on a
per-run basis with `--allow-token-auth` when you need to.
