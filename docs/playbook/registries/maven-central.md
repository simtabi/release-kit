# Maven Central

**Automation level**: API (with mandatory GPG signing)
**Source-of-truth**: `pom.xml` `<version>` / `build.gradle.kts`

## Overview

Maven Central is the canonical JVM-ecosystem registry. Two paths:

- **Central Portal** (new, 2024+) — token-based, no nexus-staging
  dance. Required for new namespaces.
- **OSSRH (Sonatype legacy)** — Jira-account-based; existing
  namespaces only. Sunsetting in 2025-2026.

Both require **GPG-signed** artifacts. Source/javadoc jars are
mandatory.

## Account & project bootstrap

### Central Portal (new namespaces)

1. Register at `https://central.sonatype.com`.
2. Verify domain ownership (TXT DNS record) to claim a `groupId`.
3. Generate a Portal API token in account settings.

### OSSRH (legacy)

1. Register Jira account at `https://issues.sonatype.org`.
2. Open an "OSSRH namespace claim" ticket for your `groupId`.
3. Wait for human approval (1-3 business days).

## Authentication options

1. **Central Portal API token** (Bearer auth) for the new path.
2. **OSSRH username + password** (HTTP Basic) for legacy.
3. **GPG private key + passphrase** for signing (required regardless of path).

Maven Central does not support OIDC trusted publishing today.

## One-time setup

### GPG key

```bash
# bash
# Generate key (RSA 4096, no passphrase if you'll store in CI without one)
gpg --full-generate-key

# Find the key id
KEYID=$(gpg --list-secret-keys --keyid-format=LONG \
  | awk '/sec/{split($2,a,"/"); print a[2]; exit}')

# Publish public key
gpg --keyserver keyserver.ubuntu.com --send-keys $KEYID
gpg --keyserver keys.openpgp.org --send-keys $KEYID

# Export private key for CI (the secret)
gpg --export-secret-keys --armor $KEYID > private.asc
```

Store `private.asc` and the passphrase as separate CI secrets:
`GPG_PRIVATE_KEY`, `GPG_PASSPHRASE`. Never commit `private.asc`.

### Gradle (`build.gradle.kts`)

```kotlin
// bash / kotlin
plugins {
    id("com.vanniktech.maven.publish") version "0.30.0"
}

mavenPublishing {
    publishToMavenCentral(host = "CENTRAL_PORTAL")  // or "DEFAULT" for OSSRH
    signAllPublications()
    coordinates("com.simtabi", "release-kit", "0.1.0")
    pom {
        name.set("release-kit")
        description.set("Multi-registry publishing automation")
        url.set("https://github.com/simtabi/release-kit")
        licenses { license { name.set("MIT"); url.set("https://opensource.org/license/mit/") } }
        developers { developer { id.set("simtabi"); name.set("Simtabi LLC") } }
        scm { url.set("https://github.com/simtabi/release-kit") }
    }
}
```

### Maven (`pom.xml`)

Sonatype's docs cover the `nexus-staging-maven-plugin` + `maven-gpg-plugin`
setup; see Central Portal docs for the new path.

## Per-release workflow

### Manual (Gradle, Central Portal)

```bash
# bash
# 1. Import GPG key (one-time per shell)
echo "$GPG_PRIVATE_KEY" | gpg --batch --import

# 2. Build + sign + publish
./gradlew \
  -PsigningInMemoryKey="$GPG_PRIVATE_KEY" \
  -PsigningInMemoryKeyPassword="$GPG_PASSPHRASE" \
  -PmavenCentralUsername="$CENTRAL_TOKEN_USER" \
  -PmavenCentralPassword="$CENTRAL_TOKEN_VALUE" \
  publishToMavenCentral
```

### CI/CD (GitHub Actions, Central Portal)

```yaml
# bash / yaml
publish-mvn:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-java@v4
      with: { distribution: temurin, java-version: '21' }
    - uses: crazy-max/ghaction-import-gpg@v6
      with:
        gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
        passphrase: ${{ secrets.GPG_PASSPHRASE }}
    - run: ./gradlew publishToMavenCentral
      env:
        ORG_GRADLE_PROJECT_mavenCentralUsername: ${{ secrets.CENTRAL_TOKEN_USER }}
        ORG_GRADLE_PROJECT_mavenCentralPassword: ${{ secrets.CENTRAL_TOKEN_VALUE }}
        ORG_GRADLE_PROJECT_signingInMemoryKey: ${{ secrets.GPG_PRIVATE_KEY }}
        ORG_GRADLE_PROJECT_signingInMemoryKeyPassword: ${{ secrets.GPG_PASSPHRASE }}
```

## Verification

```bash
# bash
# Central Portal: search.maven.org/artifact/com.simtabi/release-kit/0.1.0/jar
# CLI:
curl -fsSL "https://repo1.maven.org/maven2/com/simtabi/release-kit/0.1.0/release-kit-0.1.0.pom"
mvn dependency:get -Dartifact=com.simtabi:release-kit:0.1.0
```

Cache propagation: ~1-2 hours from upload to `repo1.maven.org`.

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Pom validation failed: license, developers, scm sections required` | Maven Central enforces full POM | Add the missing sections per Gradle config above |
| `Failed to verify signature` | GPG key not published to keyservers | `gpg --keyserver keyserver.ubuntu.com --send-keys $KEYID`; wait 30 min for replication |
| `Repository "ossrh" requires authentication` | OSSRH creds missing or wrong path | Confirm Central Portal vs OSSRH publishing target |
| `Component already exists` | Re-upload of same version | Bump; Central never lets you re-upload |
| Long propagation lag | Mirror sync is slow | Wait up to 2h; check status.maven.org |
| Build complains "no SOURCE jar" | Sources/javadoc not configured | `withSourcesJar()` and `withJavadocJar()` in Gradle |

## Security checklist

- [ ] GPG key is RSA 4096 (some keyservers reject smaller).
- [ ] Private key passphrase stored separately from the key.
- [ ] Public key published to multiple keyservers.
- [ ] Central Portal API token expires (rotate annually).
- [ ] `pom.xml` has `<scm>` pointing at the canonical repo so
      consumers can audit source.
- [ ] No `-SNAPSHOT` versions ever pushed to release repo (use
      a separate snapshot repository).

## See also

- [Central Portal docs](https://central.sonatype.org/publish/publish-portal-guide/)
- [`../cross-cutting/provenance.md`](../cross-cutting/provenance.md) — GPG isn't Sigstore; Maven's signing is its own world.
