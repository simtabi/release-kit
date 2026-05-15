# GitLab.com

| | |
|---|---|
| Class | `release_kit.platforms.git_hosts.gitlab.GitLab` |
| Slug | `gitlab` |
| Automation | `OIDC_API` |
| Mixin | [`GitLabApiMixin`](../../src/release_kit/platforms/mixins/gitlab_api.py) |

Workflow: [`../playbook/git-hosts/gitlab.md`](../playbook/git-hosts/gitlab.md).

## Config

```json
"targets": {
  "gitlab": {
    "enabled": true,
    "auth": "oidc",
    "project": "my-group/release-kit",
    "tag": "v1.4.2",
    "description": "release notes here",
    "env_var": "GITLAB_TOKEN"
  }
}
```

Use either `project` (path) or `project_id` (numeric). Path is
URL-encoded automatically.
