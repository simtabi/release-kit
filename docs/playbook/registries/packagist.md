# Packagist

**Automation level**: API (webhook-driven)
**Source-of-truth**: `composer.json` `"version"` (or git tag)

## Overview

Packagist (`packagist.org`) is the canonical Composer / PHP registry.
Unlike PyPI / npm, Packagist doesn't host the artifact itself —
it indexes git repositories. Publishing means:

1. Adding `composer.json` to a git repo.
2. Registering the repo URL on packagist.org.
3. Tagging a release in git.
4. (Optional) Triggering a refresh via webhook or API.

Reference: `composer require <vendor>/<package>`.

## Account & project bootstrap

1. Register at `https://packagist.org` (GitHub / GitLab / Bitbucket
   social login or password).
2. Enable 2FA: `Profile → Two-Factor Authentication`.
3. **Submit** the package: profile → **Submit → paste git URL**.
   Packagist reads `composer.json::name` and creates the page.
4. Set up the **GitHub Service** (or GitLab webhook, Bitbucket
   webhook) so Packagist auto-updates on push:
   - Profile → **Profile → Show API token**
   - GitHub: Settings → Webhooks → `https://packagist.org/api/github?username=<user>` with the API token

## Authentication options

1. **API token + webhook** — Packagist API token (per-account)
   stored in GitHub/GitLab/Bitbucket webhook settings. Push events
   trigger refresh.
2. **API token + manual `update-package` call** — for repos
   without webhook integration:
   ```bash
   # bash
   curl -XPOST -H'content-type:application/json' \
     "https://packagist.org/api/update-package?username=$USER&apiToken=$TOKEN" \
     -d'{"repository":{"url":"https://github.com/simtabi/php-pkg"}}'
   ```
3. **Manual "Update" button** on the package page — for occasional
   one-off refreshes.

Packagist does not support OIDC trusted publishing. The API token
authenticates an account, not a workflow.

## One-time setup

### composer.json

```json
// bash / json
{
  "name": "simtabi/release-kit",
  "description": "Multi-registry publishing automation",
  "type": "library",
  "license": "MIT",
  "keywords": ["release", "publish", "ci"],
  "authors": [{ "name": "Simtabi LLC", "email": "opensource@simtabi.com" }],
  "homepage": "https://github.com/simtabi/release-kit",
  "require": {
    "php": "^8.2"
  },
  "autoload": {
    "psr-4": { "Simtabi\\ReleaseKit\\": "src/" }
  },
  "minimum-stability": "stable",
  "support": {
    "issues": "https://github.com/simtabi/release-kit/issues",
    "source": "https://github.com/simtabi/release-kit"
  }
}
```

### Register on Packagist

1. Submit the URL via the web UI (one-time).
2. Add the GitHub webhook (Settings → Webhooks → Add):
   - Payload URL: `https://packagist.org/api/github?username=<user>`
   - Content type: `application/json`
   - Secret: your Packagist API token
   - Events: Push, Release

## Per-release workflow

### Manual

```bash
# bash
# 1. Bump
$EDITOR composer.json                  # (optional; composer can read git tag)

# 2. Commit + tag
git add -u
git commit -m "release: v1.4.2"
git tag -a v1.4.2 -m "v1.4.2"
git push origin main
git push origin v1.4.2

# 3. (Webhook auto-fires; if not, force refresh)
curl -XPOST -H'content-type:application/json' \
  "https://packagist.org/api/update-package?username=$USER&apiToken=$TOKEN" \
  -d'{"repository":{"url":"https://github.com/simtabi/release-kit"}}'
```

### CI/CD (GitHub Actions)

```yaml
# bash / yaml
publish-packagist:
  runs-on: ubuntu-latest
  steps:
    - name: Notify Packagist
      run: |
        curl -fsSL -XPOST -H'content-type:application/json' \
          "https://packagist.org/api/update-package?username=${{ vars.PACKAGIST_USER }}&apiToken=${{ secrets.PACKAGIST_TOKEN }}" \
          -d'{"repository":{"url":"https://github.com/${{ github.repository }}"}}'
```

(Usually unnecessary if the webhook is wired up; this is a belt-
and-braces backup.)

## Verification

```bash
# bash
# 1. Package page lists the new version
curl -fsSL https://packagist.org/packages/simtabi/release-kit.json \
  | jq '.package.versions | keys'

# 2. Install
composer require simtabi/release-kit:^1.4
composer show simtabi/release-kit | head -10
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| Package page shows "stale" | Webhook not firing | Re-add the webhook; check `Recent Deliveries` in GitHub for 4xx responses |
| New version doesn't appear after push | Tag missing or doesn't start with `v` | Tag must be `vX.Y.Z` or pure semver |
| `Package not found` on `composer require` | Wrong name capitalisation | Packagist names are lowercase; match `composer.json::name` exactly |
| `Conflicting branch alias` | `extra.branch-alias` in `composer.json` mismatched | Remove or align with semver branches |
| 403 on `update-package` API | Wrong API token | Regenerate at Packagist profile |

## Security checklist

- [ ] 2FA enabled on Packagist account.
- [ ] Webhook secret = your Packagist API token (it's how
      Packagist verifies the request is yours).
- [ ] API token in CI is masked, not echoed.
- [ ] `composer.json` `homepage` + `support.source` match the
      actual repo URL (Packagist auto-detects mismatches).
- [ ] Repository is public (private Packagist requires a paid
      tier).

## See also

- [Packagist docs](https://packagist.org/about)
- [Composer schema](https://getcomposer.org/doc/04-schema.md)
