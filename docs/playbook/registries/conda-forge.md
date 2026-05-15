# Conda-forge

**Automation level**: PR-based (backlog: not coded in release-kit v0.1)
**Source-of-truth**: `recipe/meta.yaml` in `conda-forge/staged-recipes`,
then a per-feedstock repo

## Overview

Conda-forge is a community-driven distribution channel for the Conda
ecosystem. Publishing is **not** API-driven: you open a PR against
`conda-forge/staged-recipes`, a bot validates the recipe, human
maintainers review, and on merge the bot creates a dedicated
"feedstock" repo (`<package>-feedstock`) that mints subsequent
releases.

This page is reference-only in v0.1 of release-kit. Conda-forge's
review cadence is heavy enough that "automation by default" would
be misleading.

## Account & project bootstrap

1. GitHub account exists.
2. Fork `https://github.com/conda-forge/staged-recipes`.
3. Add `recipes/<your-package>/meta.yaml` describing your package:

```yaml
# bash / yaml
{% set name = "release-kit" %}
{% set version = "1.4.2" %}

package:
  name: {{ name }}
  version: {{ version }}

source:
  url: https://files.pythonhosted.org/packages/source/s/simtabi-release-kit/simtabi_release_kit-{{ version }}.tar.gz
  sha256: PLACEHOLDER_SDIST_SHA256

build:
  noarch: python
  number: 0
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
  entry_points:
    - release-kit = release_kit.cli.app:app

requirements:
  host:
    - python >=3.11
    - pip
    - hatchling
  run:
    - python >=3.11
    - typer
    - pydantic >=2

test:
  imports:
    - release_kit
  commands:
    - release-kit --help

about:
  home: https://github.com/simtabi/release-kit
  license: MIT
  license_file: LICENSE
  summary: Multi-registry publishing automation
```

4. Open a PR against `staged-recipes/main`. Bots run lint + CI.
5. Wait for human review (days to weeks).
6. On merge, a `release-kit-feedstock` repo is auto-created.

## Authentication options

You don't authenticate to conda-forge; you authenticate to GitHub
to open PRs.

1. **Workflow `GITHUB_TOKEN`** for feedstock PR bumps.
2. **Fine-grained PAT** scoped to the feedstock repo.

## One-time setup

### After merge: the feedstock repo

Conda-forge bots maintain the feedstock; you become a maintainer
listed in `recipe/meta.yaml::extra.recipe-maintainers`. New
versions are usually proposed automatically by the
`regro/cf-scripts` bot when it detects a new PyPI release.

If the bot lags, push a manual update:

```bash
# bash
gh repo clone conda-forge/release-kit-feedstock
cd release-kit-feedstock
$EDITOR recipe/meta.yaml                # bump version + sha256
git checkout -b bump/1.4.2
git commit -am "bump to 1.4.2"
gh pr create --title "Bump 1.4.2" --body "Update for upstream 1.4.2"
```

CI runs build matrix (linux-64, linux-aarch64, osx-64, osx-arm64,
win-64). On green + maintainer approval, merge.

## Per-release workflow

### Initial recipe (first publish)

PR to `staged-recipes` as in **Bootstrap**. One-time.

### Subsequent versions (feedstock exists)

1. Wait for `regro-cf-autotick-bot` to open a PR (usually
   within hours of a PyPI release).
2. CI runs.
3. You (or another maintainer) merge.
4. Conda-forge bot publishes to the `conda-forge` channel.

## Verification

```bash
# bash
# 1. Channel index lists the version
conda search -c conda-forge release-kit

# 2. Install
conda install -c conda-forge release-kit=1.4.2
```

Cache propagation: ~1-2 hours from feedstock merge to
`conda.anaconda.org/conda-forge` mirrors.

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `staged-recipes` PR sits idle | Volunteer reviewer queue | Ping in `staged-recipes` issue tracker; be patient (1-2 weeks typical) |
| Build fails on `win-64` | Pure-Python `noarch` not declared | Add `build: noarch: python` for Python-only packages |
| `sha256 mismatch` | sdist re-uploaded on PyPI (rare) | Recompute sha; PyPI is immutable so this is almost always a copy-paste error |
| `regro-cf-autotick-bot` doesn't open PR | Version pattern not detected | Manual PR per "Subsequent versions" above |
| `conda install` finds an old version | Mirror lag | `conda search ... --info` shows channel timestamps |

## Security checklist

- [ ] Recipe specifies `sha256` from the immutable upstream sdist.
- [ ] `extra.recipe-maintainers` lists at least 2 humans.
- [ ] No build-time network access beyond the declared `source:` URL.
- [ ] License file shipped in the package
      (`about.license_file: LICENSE`).
- [ ] `test.commands` actually invokes the binary, not just `--help`.

## See also

- [conda-forge documentation](https://conda-forge.org/docs/)
- [`pypi.md`](pypi.md) — recipes typically point at PyPI sdists
