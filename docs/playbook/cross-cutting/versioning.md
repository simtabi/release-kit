# Release versioning

How to pick a version number, where to record it, and how to tag.

## SemVer vs. CalVer

| | SemVer | CalVer |
|---|---|---|
| Format | `MAJOR.MINOR.PATCH` (e.g. `1.4.2`) | `YYYY.MM.PATCH` (e.g. `2026.05.1`) |
| Best for | Libraries, SDKs, anything with consumers depending on API | Applications, distributions, base images, anything with no public API surface |
| Breaking change signal | Bump MAJOR | n/a (use CHANGELOG) |
| Pre-release | `1.4.2-alpha.1`, `1.4.2-rc.1` | `2026.05.0a1` |

The release-kit's own version is SemVer. ai-configurator and
get-installer use SemVer. Ubuntu, Debian, datasets, and most
"distributions" use CalVer.

If unsure, pick SemVer. CalVer is a deliberate signal that there is
no API.

## Tagging convention

Tags carry a `v` prefix: `v1.4.2`, not `1.4.2`. Reasons:

- Git sorts tags lexically; `v1`/`v2` puts version tags ahead of
  any branch named `1.0` or similar.
- Most CI tools' tag-trigger regex assumes the prefix
  (`refs/tags/v*`).
- Standard across major ecosystems (npm, PyPI, Go, Rust, .NET).

```bash
# bash
git tag -a v1.4.2 -m "v1.4.2 - what changed in one line"
git push origin v1.4.2
```

Annotated tags (`-a`) over lightweight tags. Annotated tags carry a
message + author + date and are stored as real Git objects;
lightweight tags are just refs.

## Source-of-truth for version strings

Pick one and only one:

- **`pyproject.toml` `[project].version`** (Python; preferred for
  PEP 621 packages)
- **`package.json` `"version"`** (npm)
- **`Cargo.toml` `[package].version`** (Rust)
- **`gemspec` `s.version`** (Ruby)
- **`pom.xml` `<version>`** (Maven)
- **A standalone `VERSION` file** (any language; lowest friction
  for non-typed ecosystems)
- **Dynamic from Git tags** (`hatch-vcs`, `setuptools-scm`,
  `python-semantic-release`)

release-kit's JSON config declares `project.version_source` so the
tool reads the same string the package manager will read.

```json
{
  "project": {
    "name": "my-project",
    "version_source": "pyproject.toml"
  }
}
```

Supported `version_source` values: `pyproject.toml`,
`package.json`, `Cargo.toml`, `gemspec:my-project.gemspec`,
`pom.xml`, `version-file:VERSION`, `git-tag`.

## Pre-release suffixes

| Ecosystem | Convention | Example |
|---|---|---|
| SemVer | `-alpha.N`, `-beta.N`, `-rc.N` | `1.4.2-rc.1` |
| PEP 440 (PyPI) | `aN`, `bN`, `rcN` | `1.4.2rc1` |
| npm | SemVer `-` prefix | `1.4.2-rc.1` |
| Rust / Cargo | SemVer `-` prefix | `1.4.2-alpha.1` |
| .NET / NuGet | `-` prefix; Microsoft prerelease tag | `1.4.2-preview.1` |
| Maven | `-SNAPSHOT` for in-progress; `-rcN` for release candidates | `1.4.2-rc1` |

release-kit's `publish` command warns when the version string carries
a pre-release suffix and routes to the pre-release channel where the
registry has one (npm's `--tag next`, PyPI's no separate channel but
a separate Project page on `pypi.org/project/.../#history`).

## Build metadata

Build metadata after `+` is SemVer-legal but ignored for ordering:
`1.4.2+build.42`. Don't use it for human-meaningful info; the
CHANGELOG is the right place.

## CHANGELOG.md

[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.
Every released version has its own `## [X.Y.Z] - YYYY-MM-DD`
section with `### Added`, `### Changed`, `### Fixed`, `### Removed`,
`### Security`, `### Deprecated` sub-headings as needed.

`## [Unreleased]` at the top accumulates pending entries; the
release commit moves them into a dated section. release-kit's
`publish` command refuses to proceed when the version source's
version doesn't have a matching dated section in CHANGELOG (turn
off with `policies.require_changelog: false` if you don't keep one).

## Release commit + tag flow

```bash
# bash
# 1. Bump the version in the source-of-truth file
$EDITOR pyproject.toml

# 2. Move [Unreleased] block under a dated heading
$EDITOR CHANGELOG.md

# 3. Update the link-ref at the bottom of CHANGELOG.md
# 4. Commit
git add -u
git commit -m "release: v1.4.2"

# 5. Annotated tag
git tag -a v1.4.2 -m "v1.4.2 - one-line summary"

# 6. Push branch + tag
git push origin main
git push origin v1.4.2
```

`release-kit publish` runs steps 1-6 with the values from your JSON
config (in dry-run by default; pass `--apply` to actually mutate).

## Tag policy enforcement

Many CI workflows trigger on `refs/tags/v*`. release-kit can verify
before publishing:

```json
{
  "policies": {
    "require_tag_match": true,    // tag name must equal "v" + version_source
    "require_clean_git": true,    // no uncommitted changes
    "require_signed_tag": false   // optional: refuse unsigned tags
  }
}
```

## Yanking vs deleting

| Action | Effect |
|---|---|
| **Yank** (PyPI, RubyGems, npm) | Version still resolves for `==<exact>` but is hidden from solver defaults |
| **Delete** | Version disappears completely; resolver fails |

Yank for security recalls; delete only when the version was
fundamentally wrong (e.g., contained a secret). Almost no registry
allows re-using a deleted version number — the version is burned.

## See also

- [`preflight.md`](preflight.md) — checklist that runs before any
  bump
- [`provenance.md`](provenance.md) — signing the tag + the artifact
