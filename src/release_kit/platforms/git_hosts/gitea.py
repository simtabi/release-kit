"""Gitea / Forgejo publisher.

GitHub-compatible REST API at /api/v1. Same flow whether the
instance runs Gitea or Forgejo.
@see  docs/playbook/git-hosts/gitea.md
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PublishError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, GitHost


class Gitea(GitHost):
    """
    Gitea / Forgejo host.

    Config keys (under ``targets.gitea``)::

        "host":   "codeberg.org"           # or your instance
        "owner":  "simtabi"
        "repo":   "release-kit"
        "tag":    "v1.4.2"
        "name":   "v1.4.2"
        "body":   "release notes"
        "env_var": "GITEA_TOKEN"
    """

    slug: ClassVar[str] = "gitea"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._host: str = str(extras.get("host", "")).rstrip("/")
        self._owner: str = str(extras.get("owner", ""))
        self._repo: str = str(extras.get("repo", ""))
        self._tag: str = str(extras.get("tag", ""))
        self._name: str = str(extras.get("name", self._tag))
        self._body: str = str(extras.get("body", ""))
        self._env_var: str = str(extras.get("env_var", "GITEA_TOKEN"))

    def _api_base(self) -> str:
        return f"https://{self._host}/api/v1"

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._host:
            raise AuthenticationError("gitea.host not configured", code="missing-host")
        if not self._owner or not self._repo:
            raise AuthenticationError("owner + repo required", code="missing-config")
        resolution = resolve_token("gitea", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no Gitea token resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._token = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"{self._owner}/{self._repo} on {self._host}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._tag:
            raise AuthenticationError("tag not configured", code="missing-tag")
        return StepOutcome(step="validate", status="ok", detail=f"tag={self._tag}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        path = f"/repos/{self._owner}/{self._repo}/releases"
        body = {
            "tag_name": self._tag,
            "name": self._name,
            "body": self._body,
            "draft": False,
            "prerelease": False,
        }
        if ctx.dry_run:
            return StepOutcome(
                step="publish", status="dry-run",
                detail=f"would POST {path} with tag={self._tag}",
            )
        try:
            with httpx.Client(
                timeout=30.0,
                headers={"Authorization": f"token {self._token}"},
            ) as client:
                r = client.post(self._api_base() + path, json=body)
        except httpx.HTTPError as e:
            raise PublishError(f"network error: {e}", code="gitea-api-error") from e
        if not r.is_success:
            raise PublishError(
                f"Gitea returned {r.status_code}: {r.text[:200]}",
                code="gitea-release-failed",
            )
        return StepOutcome(step="publish", status="ok", detail=f"release {self._tag} created")
