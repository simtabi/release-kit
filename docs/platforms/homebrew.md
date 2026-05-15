# Homebrew tap

| | |
|---|---|
| Class | `release_kit.platforms.registries.homebrew.Homebrew` |
| Slug | `homebrew` |
| Automation | `PR_BASED` |
| Mixin | [`GitHubApiMixin`](../../src/release_kit/platforms/mixins/github_api.py) |

Workflow: [`../playbook/registries/homebrew.md`](../playbook/registries/homebrew.md).

## Config

```json
"targets": {
  "homebrew": {
    "enabled": true,
    "auth": "token",
    "tap": "simtabi/homebrew-tap",
    "formula": "release-kit",
    "sdist_url": "https://files.pythonhosted.org/.../release_kit-X.Y.Z.tar.gz",
    "env_var": "TAP_GITHUB_TOKEN"
  }
}
```

PR-based by nature: release-kit computes the new `sha256`, opens a
PR against the tap repo updating the formula's `url` and `sha256`
lines. Merge is human-gated. v0.1 ships the sha computation +
formula-presence verification; the full auto-PR flow lands in v0.2.

`TAP_GITHUB_TOKEN` is a fine-grained PAT scoped to the tap repo
(Contents + Pull requests: Read & write).
