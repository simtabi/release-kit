# Provenance and signing

How to prove a published artifact was built from your source by your
CI, not by an attacker swapping the wheel between build and upload.

## The threat model

Without provenance:

1. Attacker compromises your developer's laptop or a CI secret.
2. Builds a malicious version with the same version number.
3. Uploads it to the registry.
4. Downstream users install the malicious build.

Detection: none until someone notices. By then the package has
been mirrored to caches, vendored into other projects, baked into
Docker images.

With provenance:

1. Each published artifact carries a cryptographic statement
   ("this `.whl` was built from `simtabi/release-kit@v1.4.2`,
   commit `abc123`, by GitHub Actions workflow `release.yml`,
   on `2026-05-15T14:30:00Z`").
2. The signing key is held by the issuer (Sigstore's Fulcio +
   Rekor public-log, or the registry's own key).
3. Verifiers reject artifacts whose claim doesn't match.

## The stack today

### Sigstore (`cosign` / `gitsign`)

Free, keyless, public-log-backed signing. Adopted by:
- npm (provenance, since 2023)
- PyPI (attestations, PEP 740, since 2024)
- Docker (Notary v2 / Sigstore for OCI artifacts)
- Conda-forge

Signature chain: your CI's OIDC ID-token → Fulcio short-lived
certificate (15 min) → Sigstore signature → Rekor public log entry.

### npm provenance

```yaml
# .github/workflows/release.yml -- npm
permissions:
  id-token: write
  contents: read

jobs:
  publish:
    steps:
      - run: npm publish --provenance --access public
```

Verify:
```bash
# bash
npm view <pkg> --json | jq .dist.attestations
```

### PyPI attestations (PEP 740)

Automatic when you publish via OIDC trusted publisher and the
`pypa/gh-action-pypi-publish@release/v1` action with default
`attestations: true`.

Verify:
```bash
# bash
pip download --no-deps simtabi-release-kit
sigstore verify identity \
  --bundle <file>.sigstore \
  --cert-identity-regexp 'https://github.com/simtabi/release-kit/.*' \
  --cert-oidc-issuer 'https://token.actions.githubusercontent.com'
```

### Container images (OCI)

```yaml
# .github/workflows/release.yml -- ghcr
- name: Build
  run: docker build -t ghcr.io/simtabi/example:${{ github.sha }} .

- name: Sign
  env:
    COSIGN_EXPERIMENTAL: "true"
  run: |
    cosign sign --yes ghcr.io/simtabi/example:${{ github.sha }}
```

Verify:
```bash
# bash
cosign verify ghcr.io/simtabi/example:<tag> \
  --certificate-identity-regexp 'https://github.com/simtabi/.+' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## SLSA levels

Supply-chain Levels for Software Artifacts. Standard maturity ladder.

| Level | Requirement | release-kit's stance |
|---|---|---|
| SLSA 1 | Build process exists and is automated | Default; CI builds everything |
| SLSA 2 | Build runs on a hosted CI; provenance generated | Achievable with GitHub Actions + Sigstore |
| SLSA 3 | Build is isolated (ephemeral runner, signed source) | Requires runner attestations |
| SLSA 4 | Hermetic builds, two-person review on the build config | Out of scope for OSS today |

For OSS, SLSA 2 is the realistic target. release-kit's bundled
`release.yml` template hits SLSA 2 automatically when you enable
provenance per platform.

## Maven Central GPG signing

Maven Central requires GPG-signed artifacts (this is **not**
Sigstore; the convention predates it).

```bash
# bash
# One-time: generate a key + publish it
gpg --gen-key                 # 4096-bit RSA, no passphrase if CI-only
KEYID=$(gpg --list-secret-keys --keyid-format=LONG | awk '/sec/{split($2,a,"/"); print a[2]; exit}')
gpg --keyserver keyserver.ubuntu.com --send-keys $KEYID

# Per-release: sign
mvn deploy -Dgpg.passphrase="$GPG_PASSPHRASE"
```

Store the **private key** and **passphrase** as separate CI secrets:
- `GPG_PRIVATE_KEY` = output of `gpg --export-secret-keys --armor $KEYID`
- `GPG_PASSPHRASE` = the passphrase

GitHub Action: `crazy-max/ghaction-import-gpg@v6`.

## Reproducible builds

Provenance proves "this build happened"; reproducibility proves
"this build's bytes are deterministic from this source". They are
complementary.

- Python: `python -m build --sdist --wheel` is mostly reproducible
  when you control `SOURCE_DATE_EPOCH`.
- Docker: BuildKit's `--output type=docker,dest=...` + a pinned
  base image SHA is mostly reproducible.
- Cargo / npm / Maven: increasingly reproducible; consult each
  project's docs.

release-kit's `publish` runs each build twice in `--reproducible`
mode and `cmp -s` the outputs. Discrepancy aborts the publish.

## Storage of long-term secrets

If you can't use OIDC (and therefore can't avoid a static signing
key):

- GPG private key: store in a hardware token (YubiKey) or in your
  CI's secret store with **environment-binding** + **required
  reviewers** on the publish job.
- Sigstore tokens: not applicable; keyless flow always uses
  short-lived OIDC.

## What release-kit does

When a target's config has `provenance: true`:

1. Build the artifact.
2. Compute its SHA256.
3. Acquire an OIDC ID-token from the CI provider.
4. Hand off to the registry's provenance endpoint (npm, PyPI) or
   to Sigstore via `cosign` (Docker / OCI).
5. Verify the signature is in Rekor (public transparency log).
6. Print the verifier command users can run locally.

Failure at any step aborts the publish; no half-signed artifact
lands on the registry.

## See also

- [`oidc-matrix.md`](oidc-matrix.md) — OIDC is the foundation that
  makes keyless signing work
- [`token-scoping.md`](token-scoping.md) — the only secret you
  can't avoid (Maven Central GPG)
- [Sigstore docs](https://docs.sigstore.dev/)
- [SLSA spec](https://slsa.dev/)
