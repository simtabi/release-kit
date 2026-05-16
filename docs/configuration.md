# Configuration

`release.json` (or any path passed to `--config`) is the single
source of truth. JSON Schema:
[`src/release_kit/schema/release-kit.schema.json`](../src/release_kit/schema/release-kit.schema.json).

## Three layers of precedence

1. **CLI flags** (`--target pypi`, `--apply`, `--allow-token-auth`)
2. **Environment variables**, loaded from `.env` in dev or from the
   CI secret store in prod
3. **JSON config** (`release.json`)

Higher numbers lose to lower numbers. CLI flags always win.

## Top-level shape

```json
{
  "$schema": "./schema/release-kit.schema.json",
  "project":  { ... },
  "targets":  { "<slug>": { ... }, "<slug>": { ... } },
  "policies": { ... }
}
```

## `project`

| Field | Type | Default | Required |
|---|---|---|:--:|
| `name` | `str` | — | ✓ |
| `version_source` | `pyproject.toml` \| `package.json` \| `Cargo.toml` \| `pom.xml` \| `git-tag` | `pyproject.toml` | |
| `version_file` | `str` | `null` | when `version_source` is non-standard |

## `targets.<slug>`

Each target is keyed by its platform slug (see
[`docs/platforms/`](platforms/) for the per-platform key list).

Common keys (all targets):

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | `bool` | `true` | When `false`, `publish` skips the target. |
| `auth` | `oidc` \| `token` \| `cli` \| `none` | `oidc` | Preferred auth method. Falls back per `policies.allow_token_auth`. |

Per-platform extras are passed through as free-form keys
(`TargetConfig` has `extra="allow"`). For example:

```json
"github": {
  "enabled": true,
  "auth": "token",
  "repo": "owner/name",
  "tag": "v1.4.2",
  "draft": false,
  "prerelease": false,
  "generate_notes": true,
  "topics": ["oss", "python"]
}
```

See each platform's page under [`docs/platforms/`](platforms/) for
its full key list.

## `policies`

Global publish-time policies enforced by the runner.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `require_clean_git` | `bool` | `true` | Refuse to publish from a dirty working tree. |
| `require_tag_match` | `bool` | `true` | Tag name must equal `v` + version source's version. |
| `require_signed_tag` | `bool` | `false` | Require gpg / ssh-signed tags. |
| `require_changelog` | `bool` | `true` | Require a dated section in `CHANGELOG.md`. |
| `continue_on_error` | `bool` | `false` | When `true`, a failing target doesn't abort siblings. |
| `default_dry_run` | `bool` | `true` | Default `publish` to dry-run unless `--apply` is set. |
| `allow_token_auth` | `bool` | `false` | When `false`, refuse to fall back from OIDC to a token without `--allow-token-auth`. |
| `parallel_publish` | `bool` | `false` | When `true`, run target lifecycles concurrently in a thread pool. Steps within a target stay sequential; only the cross-target loop parallelises. |
| `max_workers` | `int` (1..32) | `4` | Worker count when `parallel_publish` is on. |

## Token resolution

Tokens never sit in the config. Resolution order (highest first):

1. CLI `--token` override (if the platform's CLI verb accepts one).
2. `os.environ[env_var]` — the platform's primary env var, e.g.
   `PYPI_TOKEN`, `GITHUB_TOKEN`.
3. `os.environ["RELEASE_KIT_TOKEN_<KEY>"]` — generic fallback,
   `<KEY>` is the platform slug upper-cased with `-` → `_`.
4. OS keyring under service `release-kit`, account `<slug>`.

Only the **source** (env var name or keyring entry) is logged;
values never leave memory. Use `release-kit rotate-tokens` to put a
new value in the keyring.

## Validating the file

```bash
release-kit doctor              # implicit schema validation + reach check
python -c 'import json, jsonschema; \
  jsonschema.validate(json.load(open("release.json")), \
                      json.load(open("src/release_kit/schema/release-kit.schema.json")))'
```

## A complete example

```json
{
  "$schema": "./schema/release-kit.schema.json",
  "project": {
    "name": "my-package",
    "version_source": "pyproject.toml"
  },
  "targets": {
    "pypi": {
      "enabled": true,
      "auth": "oidc",
      "package": "my-package"
    },
    "ghcr": {
      "enabled": true,
      "auth": "oidc",
      "image": "ghcr.io/my-org/my-package",
      "tags": ["1.4.2", "latest"]
    },
    "github": {
      "enabled": true,
      "auth": "token",
      "repo": "my-org/my-package",
      "tag": "v1.4.2",
      "topics": ["python", "oss", "release-automation"]
    }
  },
  "policies": {
    "require_clean_git": true,
    "require_tag_match": true,
    "require_signed_tag": true,
    "continue_on_error": false,
    "default_dry_run": true,
    "allow_token_auth": false
  }
}
```
