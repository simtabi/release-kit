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

### Round 1 — quick wins (≤ 1 day total) — ✅ complete

1. ✅ **ai-config-kit Phase C** (memory clean) — `4bd6e49`
2. ✅ **ai-config-kit Phase F** (selective install) — `fca0562`
3. ✅ **ai-config-kit Phase G** (audit log) — `cb5a9e4`
4. ✅ **ai-config-kit C3** (URL validation on `bootstrap --remote`) — `74de453`
5. ✅ **ai-config-kit C4** (diff before `decisions apply --force`) — `97761cb`
6. ✅ **release-kit HEAD-probe in `doctor`** — `68cb02e`
7. ✅ **get-installer Phase L** (`.env` config loading) — `59847bb`

### Round 2 — substantial features (1–2 days each) — 10/10 ✅

8. ✅ **ai-config-kit Phase A** (settings schema validation) — `81286ec`. Lightweight allowlist-based validation since Claude Code doesn't publish an upstream JSON Schema yet; swap to `jsonschema` when one lands.
9. ✅ **ai-config-kit Phase B** (URL decision packs) — `ac0de30`. HTTPS-only, sha256-verified, 5MB cap, path-traversal guarded.
10. ✅ **ai-config-kit Phase D** (settings migrate) — `81286ec`. Framework + empty migration table; one-entry addition for future drift.
11. ✅ **ai-config-kit C1** (extract `decisions_*` types) — `ada41bb`. Six dataclasses moved to `decisions.py` (150 lines); methods stayed on `ClaudeConfig` since they touch too much state for clean extraction.
12. ✅ **ai-config-kit C2** (`--json` output mode) — `647d712`
13. ✅ **release-kit branch protection in `bootstrap-repo`** — `0cc6cd9`
14. ✅ **release-kit provenance / SBOM** as a config-driven block — `ec6dbdc`
15. ✅ **release-kit parallel publish** — `ff18d0e`
16. ✅ **get-installer Phase F** (sigstore signing) — `433d7e1` *scaffold*. Opt-in `[sigstore]` extras + `verify.sign_bundle_with_sigstore` skeleton; dry-run returns the planned .sigstore path, apply raises `NotImplementedError` with a pointer to the pending key-management ADR (so signing never silently no-ops).
17. ✅ **get-installer Phase H** (hardening + audit pass) — `c1963c3`. Explicit TLS 1.2 min, 600s subprocess timeouts on every long-running call, confirmed no `shell=True` anywhere, SECURITY.md headline-guarantees updated.

### Round 3 — long-haul items

18. ✅ **ai-config-kit Phase E** (S3 sync) — `9976632` *scaffold*. Opt-in `[s3]` extras + `ClaudeConfig.sync_to_s3` skeleton; dry-run returns, apply raises `NotImplementedError` pointing at the pending auth-design ADR. Same fail-loud pattern as #16.
19. ✅ **get-installer Phase D** (forge-aware metadata) — `08db77e` *schema bump*. registry.json gains an optional `forge: {type, owner, repo, release_tag_template, asset_pattern}` field per version. Informational today; v0.4 wires per-forge fetchers (GitHub Releases, GitLab Releases, Codeberg, Gitea). Backward-compatible.
20. ⏳ **get-installer Phase E** (multi-tenant + domain-locked installs). **Deferred** — blocks on Phase M (admin app); the cross-package contract is the registry-json + signed-URL flow. See `REPO-PROPOSAL-admin.md` in get-installer.
21. ⏳ **get-installer Phase I** (forge package distribution / git-package catalogues). **Deferred** — needs vendor-vendoring convention design first. The Phase D schema field lays groundwork; Phase I is "many forges as first-class registries".
22. ✅ **release-kit conda-forge** — `0e691b4`. New `conda-forge` platform plugin (PR-based automation level). Lifecycle: authenticate (validates feedstock + fork shape + token), validate (version + 64-char sha256), publish (dry-run prints the patch; apply raises `not-implemented` so PR creation can't half-fire), verify (queries the feedstock for an open PR matching the version). 26 platforms registered now.

### Round 4 — separate-deliverable (XL)

23. ✅ **get-installer Phase M proposal** — `08db77e`. `REPO-PROPOSAL-admin.md` in the get-installer repo captures the scope, stack, route surface, and bootstrap checklist for the sibling `simtabi/get-installer-admin` repo. Explicit "this is a proposal, not a commitment" with a "what blocks this" section so the decision-makers have the full picture. The actual repo creation + Laravel scaffolding stay out of scope (separate session + a real customer driving it).

### Cross-cutting

- ✅ **C5** — `08db77e` (in ai-config-kit). `docs/session-protocol.template.md` is the canonical source for the session-protocol + audit-checklist sections that appear in every Simtabi SPEC.md. Future SPECs reference this; current consumer SPECs stay synced with it.
- ✅ **C6** — `4b70c83`. New `tests/test_integration.py` (8 tests) for real-FS symlink edges: install/uninstall round-trips, backup/restore, idempotency, dir-symlink traversal, outside-pointing-symlink isolation, missing-src-dir refusal, apply-then-install chain.

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

## Ship state — 2026-05-16

| Package | Latest tag | PyPI | GitHub Release |
|---|---|---|---|
| `simtabi-release-kit` | `v0.3.0` | ✓ `0.3.0` | ✓ |
| `ai-config-kit` | `v0.6.0` | ⚠ NOT PUBLISHED (publisher config pending) | ✓ |
| `get-installer` | `v0.4.0` | ✓ `0.4.0` | ✓ |

This session shipped 0.2 → 0.3 → ?  on release-kit, 0.3.0 → 0.3.1 → 0.3.2 → 0.4.0 on get-installer, 0.4.2 → 0.5.0 → 0.6.0 on ai-config-kit.

## What's left

Everything code-side has been resolved this session, including the
deferred items I'd marked earlier. What remains needs external
input:

1. **ai-config-kit PyPI publisher**: configure trusted publisher on
   PyPI for project `ai-config-kit` (Owner: simtabi, Repo:
   ai-config-kit, Workflow: release.yml, Environment: pypi). Then
   `gh run rerun --failed <latest>` or cut v0.6.1.

2. **Sigstore key-management ADR** (#16): the scaffold ships in
   get-installer v0.4.0; the in-the-flesh signing flow needs a
   decision on which signing identity, key rotation cadence, and
   where the public verification key ships.

3. **S3 sync auth-design ADR** (#18): the scaffold ships in
   ai-config-kit v0.6.0; the upload flow needs an auth design
   (IAM role? STS? federated identity?).

4. **Forge per-type fetchers** (#19): registry.json's `forge` field
   is informational in v0.4.0; v0.5 of get-installer wires the
   fetchers once a real consumer needs more than the existing
   tarball-URL model.

5. **conda-forge PR automation** (#22): the platform plugin scaffold
   ships in release-kit v0.3.0; full PR creation needs careful
   merge-conflict handling. Best done with a real feedstock to test
   against.

6. **Laravel admin app** (#23): `simtabi/get-installer/REPO-PROPOSAL-admin.md`
   captures the scope when someone takes that on.

_Generated 2026-05-16. Re-verify SPEC phase markers if used as a
punch list more than a few days later — `### Phase X: ✔ <date>`
markers move as features ship._
