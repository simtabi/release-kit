# GitHub.com

| | |
|---|---|
| Class | `release_kit.platforms.git_hosts.github.GitHub` |
| Slug | `github` |
| Automation | `OIDC_API` |
| Mixin | [`GitHubApiMixin`](../../src/release_kit/platforms/mixins/github_api.py) |

Workflow: [`../playbook/git-hosts/github.md`](../playbook/git-hosts/github.md).

## Config

```json
"targets": {
  "github": {
    "enabled": true,
    "auth": "oidc",
    "repo": "owner/name",
    "tag": "v1.4.2",
    "draft": false,
    "prerelease": false,
    "generate_notes": true,
    "env_var": "GITHUB_TOKEN"
  }
}
```

Creates the GitHub Release object. Branch protection + repo topics
land in v0.2 via the `bootstrap-repo` verb.
