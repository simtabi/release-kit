# Re-audit — plans, drafts, design docs across the three repos

Audit of what was planned vs what's shipped, surfaced from each
repo's `docs/SPEC.md`, `docs/decisions.md`, `docs/shipping-checklist.md`,
`VALIDATION.md`, and inline `TODO/FIXME/placeholder` comments.

## ai-config-kit (formerly ai-configurator)

`docs/SPEC.md` declares phases A–I; H and I are done. **Unshipped:
A through G** (7 planned features).

| Phase | Feature | Effort |
|---|---|---|
| A | Schema-driven settings validation against Claude Code's upstream JSON Schema | M |
| B | Pluggable decision packs: `decisions install <url>` for community/private packs | M |
| C | Memory dir hygiene: `memory clean --older-than 90d` to prune old projects | S |
| D | `settings migrate`: detect schema-version drift + apply migrations | M |
| E | Cross-machine sync beyond git: `sync --target s3://...` | L |
| F | Selective install: `install --only commands,agents` | S |
| G | Audit log: structured JSONL of every mutation | S |

Plus 6 open issues from SPEC §5:

| ID | Where | What |
|---|---|---|
| C1 | `manager.py` (1500+ lines) | Extract `decisions_*` methods to a sibling module |
| C2 | All commands | Add `--json` output mode for scripting |
| C3 | `cli.py bootstrap` | Validate `--remote URL` is https:// or git@ before passing to git |
| C4 | `decisions apply --force` | Show a diff before applying |
| C5 | Cross-project | SPEC duplication between this + `get-installer` — factor into shared template |
| C6 | `tests/` | Integration tests for symlinks-on-real-FS edge cases |

Plus shipping-checklist: 7 unchecked items (PyPI trusted publisher,
GitHub `pypi` environment, sanity checks post-publish).

## get-installer

`docs/SPEC.md` declares phases A–M; A, B, C, J, K are done.
**Unshipped: D, E, F, G, H, I, L, M** (8 phases, includes a whole
sibling Laravel admin app).

| Phase | Feature | Effort |
|---|---|---|
| D | Forge-aware metadata (git packages — GitHub/GitLab/Bitbucket source URLs as install endpoints) | L |
| E | Multi-tenant + domain-locked installs | L |
| F | Signed releases (sigstore + cosign attestations on the bundle) | M |
| G | Web UI / admin panel — separate deliverable | XL (this IS phase M) |
| H | Hardening + audit pass: re-review all subprocess calls, TLS pins, etc. | M |
| I | Forge package distribution (git-package catalogues — vendor-installable git submodules) | L |
| L | Configuration via `.env` (not just CLI flags) | S |
| M | Sibling repo: `get-installer-admin` (Laravel 13 + Inertia + React + REST + OAuth) | XL |

## simtabi-release-kit

Shipped at v0.1.0. `VALIDATION.md` lists deferred items:

| Item | Effort |
|---|---|
| Branch protection + environment / required-reviewer flows in `bootstrap-repo` (today only topics apply for GitHub) | M |
| Scheduled rotation dashboard / GitHub Action | M |
| Provenance / SBOM as a first-class config block | M |
| conda-forge feedstock automation (manual flow documented in playbook) | L |
| HEAD-probe in `doctor` validate step (today validates local config only) | S |
| Parallel publish across targets | M |

## Cross-cutting items found

- **C5 in ai-config-kit**: SPEC's session-protocol + audit-checklist
  is duplicated between `ai-config-kit/docs/SPEC.md` and
  `get-installer/docs/SPEC.md`. If a third project adopts this
  pattern, factor into a shared template.
- **All three repos**: Shipping-checklists exist but the per-repo
  trusted-publisher step never landed on the two unpublished
  packages. Standard Simtabi PyPI-publishing guide could live at
  `simtabi/.github` org-default README and be linked-to instead of
  duplicated.

## Effort sizing legend

- **S**: < 1 hour. Mechanical or single-file.
- **M**: 2–6 hours. Spans 2–4 files, includes tests.
- **L**: 1–2 days. New module / new CLI surface / new subsystem.
- **XL**: Multi-week. Separate deliverable / sibling repo.

## Proposed plan

A path that respects the user's scope-discipline preference (no
big-bang sweeps; ship small, verify, repeat):

### Round 1 — quick wins (≤ 1 day total)

1. **ai-config-kit Phase C** (memory clean) — single command + tests.
2. **ai-config-kit Phase F** (selective install) — flag on existing
   `install` verb.
3. **ai-config-kit Phase G** (audit log) — structured JSONL appended
   on every mutation.
4. **ai-config-kit C3** (URL validation on `bootstrap --remote`).
5. **ai-config-kit C4** (diff before `decisions apply --force`).
6. **release-kit HEAD-probe in `doctor`** (small extension).
7. **get-installer Phase L** (`.env` config loading, mirrors what
   release-kit already does via `python-dotenv`).

### Round 2 — substantial features (1–2 days each)

8. **ai-config-kit Phase A** (schema-driven settings validation).
9. **ai-config-kit Phase B** (pluggable decision packs from URLs).
10. **ai-config-kit Phase D** (settings.json migrate).
11. **ai-config-kit C1** (extract `decisions_*` from manager.py).
12. **ai-config-kit C2** (`--json` output mode across CLI).
13. **release-kit branch protection in `bootstrap-repo`**.
14. **release-kit provenance / SBOM** as a config-driven block.
15. **release-kit parallel publish**.
16. **get-installer Phase F** (signed releases via sigstore).
17. **get-installer Phase H** (hardening + audit pass).

### Round 3 — long-haul items (multi-day, optional now)

18. **ai-config-kit Phase E** (S3 sync — needs auth design).
19. **get-installer Phase D** (forge-aware metadata).
20. **get-installer Phase E** (multi-tenant + domain-locked).
21. **get-installer Phase I** (forge package distribution).
22. **release-kit conda-forge automation** (needs feedstock fork).

### Round 4 — separate-deliverable (XL)

23. **get-installer Phase M**: `get-installer-admin` — Laravel 13 +
    Inertia + React + REST API + OAuth. Not a Python package; this
    is a whole new repo.

### Cross-cutting (do once)

- **C5**: extract the session-protocol/audit-checklist boilerplate
  to a shared template living in `simtabi/.github` org-default repo,
  then trim duplicates from per-project SPECs.
- **C6** (ai-config-kit) + integration tests in release-kit + Linux
  CI runner for get-installer: harmonise the integration-test layers.

## What I recommend doing next

Round 1 (7 small items) — same-session deliverable. Each touches
≤ 4 files, has clear tests, doesn't require external setup. After
those land:

- Pause to ship v0.4.3 / v0.3.1 / v0.1.1 once you've configured the
  PyPI trusted publishers.
- Then pick from Round 2 in priority order.

Round 4 (the Laravel admin app) is a separate planning conversation.

_Generated 2026-05-16. Re-verify SPEC phase markers if used as a
punch list more than a few days later — `### Phase X: ✔ <date>`
markers move as features ship._
