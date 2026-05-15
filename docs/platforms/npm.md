# npm (registry.npmjs.org)

| | |
|---|---|
| Class | `release_kit.platforms.registries.npm.Npm` |
| Slug | `npm` |
| Automation | `OIDC_API` (provenance via setup-node) |
| Mixin | [`NpmPublishMixin`](../../src/release_kit/platforms/mixins/npm_publish.py) |

Workflow + onboarding: [`../playbook/registries/npm.md`](../playbook/registries/npm.md).

## Config

```json
"targets": {
  "npm": {
    "enabled": true,
    "auth": "oidc",
    "package_dir": ".",
    "access": "public",
    "provenance": true,
    "env_var": "NPM_TOKEN"
  }
}
```

| Key | Required | Default | Meaning |
|---|---|---|---|
| `package_dir` | no | `.` | Where `package.json` lives |
| `access` | no | `public` | `public` or `restricted` |
| `provenance` | no | `false` | OIDC provenance (GitHub Actions only) |
| `env_var` | no | `NPM_TOKEN` | |
