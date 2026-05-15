# Homebrew tap

**Automation level**: PR-based
**Source-of-truth**: `Formula/<name>.rb` in a tap repo

## Overview

A Homebrew tap is a GitHub repository named `homebrew-<tap-name>`
containing one or more `.rb` formula files. Users add it with
`brew tap <owner>/<tap-name>` and install with
`brew install <owner>/<tap-name>/<formula>`.

There is no central "tap registry" — discovery is via the user
knowing the tap name. Best for **first-party tools** you own (vs.
trying to land in homebrew/core, which has high review bar and
slow cadence).

## Account & project bootstrap

1. GitHub account / org exists.
2. Create the tap repo. The name **must** be `homebrew-<something>`:
   ```bash
   # bash
   gh repo create simtabi/homebrew-tap --public \
     --description "Simtabi Homebrew tap" \
     --clone
   ```
3. Inside the repo, create `Formula/` directory.
4. Add a formula per package: `Formula/release-kit.rb`.

## Authentication options

The tap repo is just a GitHub repo. Auth maps to the GitHub PAT /
fine-grained token / `GITHUB_TOKEN` model:

1. **Workflow `GITHUB_TOKEN` with cross-repo PAT** for the automation
   that opens the bump-version PR.
2. **Fine-grained PAT** scoped to the tap repo with `Contents: Read
   & write` + `Pull requests: Read & write`.
3. **Classic PAT** with `repo` scope — broader than needed.

## One-time setup

### Initial formula (manual; replace placeholders per release)

```ruby
# bash
# Formula/release-kit.rb
class ReleaseKit < Formula
  include Language::Python::Virtualenv

  desc "Multi-registry publishing automation"
  homepage "https://github.com/simtabi/release-kit"
  url "https://files.pythonhosted.org/packages/source/s/simtabi-release-kit/simtabi_release_kit-0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SDIST_SHA256"
  license "MIT"
  head "https://github.com/simtabi/release-kit.git", branch: "main"

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/release-kit version")
  end
end
```

Generate resource blocks from `pyproject.toml`:

```bash
# bash
brew tap-new simtabi/homebrew-tap            # if not already tapped locally
brew update-python-resources Formula/release-kit.rb
brew style --fix Formula/release-kit.rb
brew audit --new --strict Formula/release-kit.rb
```

Commit + push to the tap.

### Cross-repo PAT (for CI automation)

The publisher repo's workflow opens a PR against the tap repo. The
default `GITHUB_TOKEN` can't push to a different repo. Generate a
fine-grained PAT scoped to:

- Repository: `simtabi/homebrew-tap` only
- Permissions: Contents: Read & write, Pull requests: Read & write
- Expiry: 90 days

Store as `TAP_GITHUB_TOKEN` in the **publisher repo's** secrets.

## Per-release workflow

### Manual

```bash
# bash
# 1. Compute the new sdist URL + sha
VERSION=0.1.0
PKG=simtabi-release-kit
SDIST_URL="https://files.pythonhosted.org/packages/source/${PKG:0:1}/${PKG//-/_}/${PKG//-/_}-${VERSION}.tar.gz"
SHA=$(curl -fsSL "$SDIST_URL" | shasum -a 256 | awk '{print $1}')

# 2. Update the formula
cd ~/work/homebrew-tap
sed -i "s|url \".*\"|url \"$SDIST_URL\"|" Formula/release-kit.rb
sed -i "s|sha256 \".*\"|sha256 \"$SHA\"|" Formula/release-kit.rb

# 3. Update resources if dependencies changed
brew update-python-resources Formula/release-kit.rb

# 4. Lint
brew style --fix Formula/release-kit.rb
brew audit --strict Formula/release-kit.rb

# 5. Commit + push
git add Formula/release-kit.rb
git commit -m "release-kit: bump to $VERSION"
git push
```

### CI/CD (from publisher repo to tap repo)

```yaml
# bash / yaml
# .github/workflows/release.yml (in simtabi/release-kit)
bump-homebrew:
  needs: pypi-publish
  runs-on: ubuntu-latest
  if: startsWith(github.ref, 'refs/tags/v')
  steps:
    - uses: dawidd6/action-homebrew-bump-formula@v3
      with:
        token: ${{ secrets.TAP_GITHUB_TOKEN }}
        tap: simtabi/homebrew-tap
        formula: release-kit
        tag: ${{ github.ref_name }}
        revision: ${{ github.sha }}
```

The action opens a PR against the tap with the new `url` + `sha256`.
Merge after CI on the tap passes.

## Verification

```bash
# bash
brew update
brew tap simtabi/tap                                 # one-time
brew install simtabi/tap/release-kit
brew test simtabi/tap/release-kit
release-kit --version                                # confirms install
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Error: SHA256 mismatch` | `sha256` in formula doesn't match downloaded sdist | Recompute `shasum -a 256 <sdist>` and update |
| `brew audit` complains "long description" | Formula `desc` field too long | ≤80 chars, no trailing period |
| `update-python-resources` adds wrong deps | Resolver disagreement with pyproject | Re-run after `pip download <pkg>` to confirm full transitive set |
| PR fails to open | Cross-repo PAT not present in publisher repo secrets | Add `TAP_GITHUB_TOKEN` per setup above |
| `brew install` finds wrong tap version | Cached old tap | `brew untap simtabi/tap && brew tap simtabi/tap` |

## Security checklist

- [ ] Tap repo is public; formulas should not contain secrets.
- [ ] Cross-repo PAT is fine-grained, expiring, and scoped to the
      tap repo only.
- [ ] CI on the tap repo runs `brew audit --strict` before merge.
- [ ] `head` URL points at the canonical source repo (so users on
      `--HEAD` aren't fed a fork).
- [ ] Formula's `test do` block actually exercises the installed
      binary, not just `--version`.

## See also

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [`pypi.md`](pypi.md) — formula `url` points at PyPI sdist
- [`../git-hosts/github.md`](../git-hosts/github.md) — tap-repo settings
