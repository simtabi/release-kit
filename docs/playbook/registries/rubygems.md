# RubyGems

**Automation level**: OIDC + API
**Source-of-truth**: `<gem>.gemspec` `spec.version`

## Overview

RubyGems.org is the canonical Ruby registry. Free publishing for
public gems. Reference: `gem install <name>`.

OIDC trusted publishing (RubyGems → GitHub Actions) launched in
March 2024 and is the recommended path.

## Account & project bootstrap

1. Register at `https://rubygems.org/sign_up`.
2. Enable MFA: `Edit profile → Multifactor authentication →
   UI and gem signin`.
3. Reserve the name with the first push (no separate claim step).
4. Add additional owners after first push:
   `gem owner -a other@email.com mygem`.

## Authentication options (ranked)

1. **OIDC trusted publisher** (since 2024).
2. **Per-gem API key** with scope `Push rubygem` for a specific gem.
3. **Account-wide API key** — first push only.

## One-time setup

### OIDC (GitHub Actions)

RubyGems side:
1. Log in to rubygems.org.
2. Profile → `OIDC Trusted publishers → Add`.
3. Fields:
   - Repository owner: `simtabi`
   - Repository name: `my-gem`
   - Workflow filename: `release.yml`
   - Environment name: `rubygems`
4. Save.

GitHub side:

```yaml
# bash / yaml
publish-rubygems:
  runs-on: ubuntu-latest
  environment: rubygems
  permissions:
    id-token: write
    contents: read
  steps:
    - uses: actions/checkout@v4
    - uses: ruby/setup-ruby@v1
      with: { ruby-version: '3.3', bundler-cache: true }
    - uses: rubygems/release-gem@v1
      # Reads OIDC token automatically; no API key needed
```

### API key (manual)

```bash
# bash
gem signin                                       # interactive
# OR write directly
echo ":rubygems_api_key: rubygems_YOUR-KEY-HERE" > ~/.gem/credentials
chmod 600 ~/.gem/credentials
```

## Per-release workflow

### Manual

```bash
# bash
$EDITOR lib/mygem/version.rb            # bump VERSION constant
gem build mygem.gemspec                 # produces mygem-1.4.2.gem
gem push mygem-1.4.2.gem
```

### CI/CD

The OIDC workflow above; triggers on tag push.

## Verification

```bash
# bash
gem search mygem                                  # latest version surfaces
gem fetch mygem -v 1.4.2
gem install mygem -v 1.4.2
ruby -e "require 'mygem'; puts MyGem::VERSION"
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Repushing of gem versions is not allowed` | Re-upload same version | Bump |
| `You do not have permission to push to this gem` | Not listed as owner | `gem owner -a` from an existing owner's account |
| `MFA OTP required` (interactive) | Account has UI+gem MFA but pushing from CLI without OTP | Use API key (which bypasses OTP) or update MFA level |
| `Trusted publisher mismatch` | OIDC claims don't match policy | Inspect the issued ID-token; verify `repository`, `workflow`, `environment` |
| `Gem name too similar to <existing>` | RubyGems anti-typosquat | Choose a more distinct name |

## Security checklist

- [ ] MFA enabled at `UI and gem signin` level.
- [ ] OIDC trusted publisher configured if you use GitHub Actions.
- [ ] API keys (if used) are per-gem scoped, not account-wide.
- [ ] `.gem/credentials` is `chmod 600`.
- [ ] Gem signed (Marshalable signing or Sigstore-equivalent
      RubyGems attestations once GA).
- [ ] `gemspec`'s `metadata` block has `"source_code_uri"` and
      `"changelog_uri"` for audit traceability.

## See also

- [`../cross-cutting/oidc-matrix.md`](../cross-cutting/oidc-matrix.md)
- [RubyGems OIDC docs](https://guides.rubygems.org/trusted-publishing/)
