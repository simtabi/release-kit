# crates.io (Cargo)

**Automation level**: API
**Source-of-truth**: `Cargo.toml` `[package].version`

## Overview

`crates.io` is the canonical Rust registry. Free; one global
namespace (no scoping). Name is first-come-first-served.

Reference: `cargo install <name>` or as a dep:
`[dependencies] foo = "1.4.2"`.

## Account & project bootstrap

1. Sign in at `https://crates.io` with a GitHub account (only auth
   mechanism).
2. Generate API token: profile → **Account Settings → API Tokens
   → New Token**. Scope to the operations you need
   (`publish-new` for first push, `publish-update` for subsequent).
3. Reserve the name with the **first publish**. crates.io has a
   "yank but no delete" policy: a name, once published, is held
   for as long as the user account exists.

## Authentication options

1. **Scoped API token** (per-crate scoping landed 2023).
2. **Account-wide API token** — for first publish only.

crates.io does not support OIDC trusted publishing today.

## One-time setup

```bash
# bash
cargo login crates-io-YOUR-TOKEN-HERE
# Writes ~/.cargo/credentials.toml (chmod 600 automatic)
```

Or set the env var on each command:

```bash
# bash
export CARGO_REGISTRY_TOKEN=crates-io-YOUR-TOKEN-HERE
cargo publish
```

## Per-release workflow

### Manual

```bash
# bash
# 1. Bump
$EDITOR Cargo.toml                     # version = "1.4.2"

# 2. Pre-flight
cargo test
cargo clippy -- -D warnings
cargo doc --no-deps
cargo package --list                   # what's about to be uploaded

# 3. Publish
cargo publish
```

`cargo publish` does a wet-run upload by default. There's no
"dry-run mode" flag; `--dry-run` parses + packages but skips
upload.

### CI/CD (GitHub Actions)

```yaml
# bash / yaml
publish-crate:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: dtolnay/rust-toolchain@stable
    - run: cargo test
    - run: cargo publish --token ${{ secrets.CARGO_TOKEN }}
```

## Verification

```bash
# bash
# 1. Cache propagation: usually < 1 minute
cargo search release-kit | head -1

# 2. Install
cargo install release-kit --version 1.4.2

# 3. crates.io page
curl -fsSL "https://crates.io/api/v1/crates/release-kit" \
  | jq '.crate.max_version'
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `crate name too similar to existing crate` | crates.io enforces typo distance | Pick a more distinct name |
| `the remote server responded with: 400 BAD REQUEST: invalid upload request: missing or empty metadata` | `Cargo.toml` missing description / license | Add `description`, `license`, `repository` keys |
| `403 Forbidden` | Token scope doesn't include `publish-update` | Regenerate with right scope |
| Slow `cargo publish` (>2 min) | Vendoring dependencies into the package | `cargo package --list`; trim with `[package].exclude` |
| `unused dependency` warning blocks publish | Stricter publish settings | Remove or `[features]` gate it |

## Security checklist

- [ ] API token is scoped to specific crates (per-crate token).
- [ ] Token has expiry (rotation cadence: 90 days).
- [ ] `Cargo.toml` `[package].metadata` includes `repository`,
      `documentation`, `homepage`, `readme`.
- [ ] `cargo audit` runs in CI; release blocked on critical vulns.
- [ ] `Cargo.toml::[package].exclude` keeps build artifacts and
      `.env` out of the uploaded `.crate`.

## See also

- [crates.io publishing docs](https://doc.rust-lang.org/cargo/reference/publishing.html)
- [`../cross-cutting/oidc-matrix.md`](../cross-cutting/oidc-matrix.md) — crates.io OIDC is not yet GA
