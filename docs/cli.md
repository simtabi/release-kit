# CLI reference

Every verb. Every flag.

## Global options

These work on any subcommand:

| Flag | Purpose |
|---|---|
| `--config / -c <path>` | Path to `release.json` (default: `./release.json`). |
| `--env-file <path>` | Path to a `.env` file (default: search order — see [security.md](security.md)). |
| `--help` | Print help for that verb. |

## `release-kit init`

Scaffold a `release.json` and `.env-example` in the target directory.

```bash
release-kit init [--dir PATH] [--force]
```

| Flag | Default | Purpose |
|---|---|---|
| `--dir` | `.` | Where to write the files. |
| `--force` | `false` | Overwrite existing `release.json` / `.env-example`. |

Idempotent unless `--force`. Always adds `.env` to `.gitignore` if
absent.

## `release-kit doctor`

Per-target readiness check. Exits non-zero on RED; AMBER is a
warning.

```bash
release-kit doctor [--config PATH] [--env-file PATH]
```

Output columns: `target | class | automation | status | detail`.

| Status | Meaning |
|---|---|
| GREEN | Auth + validate succeeded; ready to publish. |
| AMBER | Validate-time warning; can still publish, but a detail (e.g. missing optional field) merits review. |
| RED | Hard failure: token missing, plugin missing, etc. |
| DISABLED | `targets.<slug>.enabled = false`. |

## `release-kit publish`

Run the publish flow across all enabled targets, or a subset.

```bash
release-kit publish [--target NAME ...] [--apply] [--config PATH]
```

| Flag | Default | Purpose |
|---|---|---|
| `--target` | every enabled | Restrict to these slugs. Repeatable. |
| `--apply` | dry-run | Actually perform mutations. |

Dry-run is the default and runs every step end-to-end without
calling registries / git hosts. Exits non-zero if any target's
flow failed.

## `release-kit verify`

Run each target's `verify` step in isolation. Useful after a
publish to confirm propagation, or as a periodic liveness check.

```bash
release-kit verify [--target NAME ...] [--config PATH]
```

| Flag | Default | Purpose |
|---|---|---|
| `--target` | every enabled | Restrict to these slugs. Repeatable. |

Skips authenticate / validate / publish. Always runs against the
real registry (no dry-run mode — verify is read-only by design).
Exits non-zero when any target's `verify()` returns `status="failed"`.

## `release-kit bootstrap-repo`

Apply declarative repo settings (topics + branch protection) per
git-host target.

```bash
release-kit bootstrap-repo [--apply] [--config PATH]
```

| Flag | Default | Purpose |
|---|---|---|
| `--apply` | dry-run | Actually call the host's API. |

GitHub-flavoured hosts support two settings, both opt-in via target
extras:

- `topics: ["oss", "python"]` — repo topics (PUT `/repos/{repo}/topics`)
- `branch_protection: { branch: main, ... }` — full branch
  protection schema (PUT `/repos/{repo}/branches/{branch}/protection`).
  The `branch` key is stripped from the payload; everything else
  passes through to GitHub's API. See
  <https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection>
  for the field list (`required_status_checks`, `enforce_admins`,
  `required_pull_request_reviews`, `restrictions`, …).

Other hosts produce a uniform "skipped — not yet implemented"
outcome so the report stays consistent.

### Example

```json
"github": {
  "enabled": true,
  "auth": "token",
  "repo": "my-org/my-package",
  "tag": "v1.4.2",
  "topics": ["oss", "python", "release-automation"],
  "branch_protection": {
    "branch": "main",
    "enforce_admins": true,
    "required_status_checks": {
      "strict": true,
      "contexts": ["ci"]
    },
    "required_pull_request_reviews": {
      "required_approving_review_count": 1,
      "require_code_owner_reviews": false
    },
    "restrictions": null
  }
}
```

## `release-kit rotate-tokens`

Interactive token rotation. For each selected platform: opens the
management URL, prompts for the new token (silent input), and
stores it via the OS keyring.

```bash
release-kit rotate-tokens [--platform SLUG ...] [--list]
```

| Flag | Default | Purpose |
|---|---|---|
| `--platform / -p` | every known | Rotate only these. Repeatable. |
| `--list` | `false` | Print the rotation table and exit. |

Blank input skips a platform without writing to the keyring. The
new value is never echoed.

## `release-kit version`

Print the package version.

```bash
$ release-kit version
simtabi-release-kit 0.1.0
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (every step ok / dry-run / skipped). |
| `1` | At least one target's flow failed. |
| `2` | Config / argument error (file missing, unknown target, schema violation). |
| `130` | User interrupt (SIGINT). |
