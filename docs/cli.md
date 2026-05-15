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

Apply declarative repo settings (topics, etc.) per git-host target.

```bash
release-kit bootstrap-repo [--apply] [--config PATH]
```

| Flag | Default | Purpose |
|---|---|---|
| `--apply` | dry-run | Actually call the host's API. |

v0.1 supports GitHub topics. Other hosts produce a uniform
"skipped — not yet implemented" outcome so the report stays
consistent.

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
