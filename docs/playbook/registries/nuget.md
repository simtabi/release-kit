# NuGet.org

**Automation level**: API
**Source-of-truth**: `.csproj` `<Version>` or `.nuspec`

## Overview

NuGet.org is the canonical .NET registry. Free public publishing.
Reference: `dotnet add package <Id>` or `Install-Package <Id>`.

Package IDs are case-insensitive and globally unique. Prefer
dotted org-prefixed names (`Simtabi.ReleaseKit`).

## Account & project bootstrap

1. Sign in at `https://www.nuget.org` with a Microsoft account.
2. Generate API key: profile → **API Keys → Create**:
   - Key name: `release-kit-publish`
   - Permission: `Push new packages and package versions`
   - Glob: `Simtabi.*` (scope to your prefix; narrowest you can use)
   - Expiry: 365 days max
3. Reserve a **package ID prefix** (corporate / verified) via
   the support form if you want to lock down `Simtabi.*` to your
   account.

## Authentication options

1. **API key with glob-pattern scope** (e.g., `Simtabi.*`).
2. **API key, account-wide** — first publish only.
3. **Microsoft account password** — never used for `dotnet nuget
   push`.

NuGet.org does not support OIDC trusted publishing today.

## One-time setup

```bash
# bash
# Store the API key in your local NuGet config
dotnet nuget setapikey nuget-YOUR-KEY-HERE \
  --source https://api.nuget.org/v3/index.json
```

Or pass on each push (preferred in CI; no on-disk storage):

```bash
# bash
dotnet nuget push *.nupkg \
  --api-key $NUGET_API_KEY \
  --source https://api.nuget.org/v3/index.json
```

## Per-release workflow

### Manual

```bash
# bash
# 1. Bump
$EDITOR src/MyPackage/MyPackage.csproj      # <Version>1.4.2</Version>

# 2. Build + pack
dotnet build -c Release
dotnet pack -c Release -o ./out

# 3. Sanity
dotnet nuget verify ./out/MyPackage.1.4.2.nupkg
unzip -l ./out/MyPackage.1.4.2.nupkg | head -20

# 4. Push
dotnet nuget push ./out/MyPackage.1.4.2.nupkg \
  --api-key $NUGET_API_KEY \
  --source https://api.nuget.org/v3/index.json
```

### CI/CD (GitHub Actions)

```yaml
# bash / yaml
publish-nuget:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-dotnet@v4
      with: { dotnet-version: '8.0.x' }
    - run: dotnet test -c Release
    - run: dotnet pack -c Release -o out
    - run: |
        dotnet nuget push out/*.nupkg \
          --api-key ${{ secrets.NUGET_API_KEY }} \
          --source https://api.nuget.org/v3/index.json \
          --skip-duplicate
```

## Verification

```bash
# bash
# 1. Page exists at https://www.nuget.org/packages/Simtabi.ReleaseKit/1.4.2
# 2. CLI install
dotnet add package Simtabi.ReleaseKit --version 1.4.2
# 3. Indexing lag: ~5-15 minutes for new versions to be searchable
```

## Common failure modes & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `409 Conflict` | Re-upload of same version | Bump |
| `403 Forbidden` | API key glob doesn't include this package ID | Regenerate with broader glob or specific ID |
| `400 Bad Request: missing icon` | NuGet quality gate | Add `<PackageIcon>` to `.csproj` |
| Package shows as "unlisted" | Auto-unlisted by NuGet for ToS violation or quality issue | Open a support ticket; usually metadata-related |
| Symbol package push fails | Symbol API key missing | Generate a separate key with "Push symbol package" permission |

## Security checklist

- [ ] API key uses glob-pattern scope, not account-wide.
- [ ] API key expiry ≤ 1 year.
- [ ] Package signed (`dotnet nuget sign`) with a code-signing
      cert if you maintain one.
- [ ] `.csproj` includes `<RepositoryUrl>`, `<RepositoryType>`,
      `<PackageLicenseExpression>`.
- [ ] Symbol package pushed too (debug symbols help downstream
      users; .snupkg).
- [ ] `nuget.config` doesn't carry a real API key (use env var
      `NUGET_API_KEY`).

## See also

- [NuGet docs](https://learn.microsoft.com/nuget/)
- [`../cross-cutting/token-scoping.md::NuGet`](../cross-cutting/token-scoping.md)
