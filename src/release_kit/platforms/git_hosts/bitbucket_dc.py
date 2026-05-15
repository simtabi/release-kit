"""Bitbucket Data Center publisher.

Different REST API than Bitbucket Cloud (v1.0 under /rest/api/).
@see  docs/playbook/git-hosts/bitbucket-dc.md
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PlatformError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, GitHost


class BitbucketDataCenter(GitHost):
    """
    Self-hosted Bitbucket Data Center.

    Config keys (under ``targets.bitbucket-dc``)::

        "host":     "bitbucket.example.com"
        "project":  "PROJ"
        "repo":     "release-kit"
        "tag":      "v1.4.2"
        "env_var":  "BITBUCKET_DC_TOKEN"
    """

    slug: ClassVar[str] = "bitbucket-dc"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._host: str = str(extras.get("host", "")).rstrip("/")
        self._project: str = str(extras.get("project", ""))
        self._repo: str = str(extras.get("repo", ""))
        self._tag: str = str(extras.get("tag", ""))
        self._env_var: str = str(extras.get("env_var", "BITBUCKET_DC_TOKEN"))

    def _api_base(self) -> str:
        return f"https://{self._host}/rest/api/1.0"

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._host:
            raise AuthenticationError("bitbucket-dc.host not configured", code="missing-host")
        if not self._project or not self._repo:
            raise AuthenticationError("project + repo required", code="missing-config")
        resolution = resolve_token("bitbucket-dc", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no HTTP Access Token resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._token = resolution.value
        return StepOutcome(step="authenticate", status="ok", detail=f"{self._project}/{self._repo}")

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._tag:
            raise AuthenticationError("tag not configured", code="missing-tag")
        return StepOutcome(step="validate", status="ok", detail=f"tag={self._tag}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        path = f"/projects/{self._project}/repos/{self._repo}/tags/{self._tag}"
        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would verify {path}",
            )
        url = self._api_base() + path
        try:
            with httpx.Client(
                timeout=30.0, headers={"Authorization": f"Bearer {self._token}"}
            ) as client:
                r = client.get(url)
        except httpx.HTTPError as e:
            raise PlatformError(f"network error: {e}", code="bitbucket-dc-api-error") from e
        if r.status_code == 404:
            raise PlatformError(
                f"tag {self._tag} not found in {self._project}/{self._repo}",
                code="tag-not-pushed",
            )
        if not r.is_success:
            raise PlatformError(
                f"Bitbucket DC returned {r.status_code}: {r.text[:200]}",
                code="bitbucket-dc-api-error",
            )
        return StepOutcome(step="publish", status="ok", detail=f"tag {self._tag} present")
