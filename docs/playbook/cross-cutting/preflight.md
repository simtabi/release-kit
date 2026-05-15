# Pre-flight checklist

What to verify before any first publish. `release-kit doctor`
automates almost all of this; run it before every release.

## The list

### Source state

- [ ] Working tree is clean (`git status` shows nothing).
- [ ] Branch is the release branch (`main` by convention).
- [ ] Local branch is up to date with `origin` (`git fetch && git status`).
- [ ] No uncommitted dependency changes (lockfile in sync with manifest).

### Version

- [ ] Version string in the source-of-truth file is bumped.
- [ ] No pre-existing tag with the same name (`git rev-parse v$VERSION`).
- [ ] CHANGELOG has a dated `## [$VERSION] - YYYY-MM-DD` section.
- [ ] Pre-release suffix (if any) matches your intent.

### Quality gates

- [ ] Tests pass on every supported platform.
- [ ] Coverage gate met.
- [ ] Linter (ruff / eslint / clippy / rubocop / phpcs) is clean.
- [ ] Type checker (mypy / tsc / cargo check) is clean.
- [ ] No banned phrases in user-facing prose (see your
      humanistic-style ruleset).
- [ ] No `TODO`, `FIXME`, or `XXX` in changed lines (your call).

### Build artefacts

- [ ] `python -m build` (or equivalent) produces both sdist and
      wheel without warnings.
- [ ] Built artefact's metadata (description, URL, authors, license)
      matches your project conventions.
- [ ] `twine check dist/*` (PyPI) or `npm pack --dry-run` (npm)
      passes.
- [ ] No secret files (`.env`, `*.key`, `*.pem`) accidentally
      bundled. Run a `unzip -l dist/*.whl | grep -E '\.(env|key|pem)$'`
      check.

### Credentials

- [ ] CI's OIDC trust policy for the target registry is configured
      (preferred path).
- [ ] If OIDC isn't available: the token is in CI's secret store
      with appropriate scoping. See
      [`token-scoping.md`](token-scoping.md).
- [ ] Token has at least the minimum scope for `publish` (not more).
- [ ] Token hasn't expired or rotated in the last hour.
- [ ] Local `.env` (if used for dev) is gitignored and `chmod 600`.

### Registry state

- [ ] Project page exists on the registry, or you're doing the
      bootstrap publish.
- [ ] Project name doesn't squat over a typo (check the registry
      for similar-spelled names).
- [ ] Trademark / naming policy of the registry doesn't conflict
      with your name.
- [ ] You can install the **previous** version successfully from
      the registry (rules out registry-side outages).

### Documentation

- [ ] README installation instructions reference the new version
      indirectly (`pip install <pkg>`, not `pip install <pkg>==1.4.1`).
- [ ] Migration guide (if breaking change) is in place.
- [ ] API reference (if generated) is regenerated.

### Communication

- [ ] Release notes (from CHANGELOG dated section) are ready to
      paste into GitHub Releases / GitLab Releases.
- [ ] If this release fixes a CVE, the SECURITY.md disclosure
      cadence has been followed.
- [ ] Downstream consumers (your other projects, public users) are
      warned of breaking changes via the appropriate channel.

### Reversibility

- [ ] You know how to yank this version if a bug surfaces in the
      first 24h.
- [ ] You have the credentials needed to yank (some registries
      require the same token that published).

## When release-kit handles it

```bash
release-kit doctor
```

Output is a per-target table:

```text
target          status  detail
pypi            GREEN   OIDC trust policy resolves; version 1.4.2 not yet published; CHANGELOG dated
npm             AMBER   token expires in 7 days; rotate via `release-kit rotate-tokens npm`
ghcr            GREEN   workflow GITHUB_TOKEN scope packages:write present
homebrew        AMBER   PR-based; will open PR against simtabi/homebrew-tap (requires merge)
maven-central   RED     GPG key fingerprint mismatch; expected <SHA>, found <other>
```

GREEN = ready to apply. AMBER = ready but verify the warning. RED
= will fail; do not run `publish --apply`.

## What release-kit can't check

- **Trademark conflicts**: the package name might be your right to
  use even though it parses cleanly. Human-only check.
- **Downstream consumer compatibility**: only your own integration
  tests prove the new version doesn't break callers.
- **Registry-side outages**: doctor reports the previous version's
  installability, not the future upload's. If the registry is down
  during the window between doctor and publish, you'll see it then.
- **GPG key rotation**: Maven Central caches your published key; a
  rotation gap of < ~2h may cause spurious verification failures
  even when local doctor is GREEN.

## See also

- [`versioning.md`](versioning.md) — picking the version
- [`provenance.md`](provenance.md) — proving the artifact's origin
- [`secrets.md`](secrets.md) — where the credentials live
- Per-platform pages under [`../registries/`](../registries/) —
  exact registry-specific verification steps
