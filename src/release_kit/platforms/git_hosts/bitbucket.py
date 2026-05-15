"""Bitbucket Cloud publisher.

Bitbucket has no first-class "Release" object like GitHub or GitLab;
the convention is "tag pushed + downloads asset uploaded". This
class handles the tag verification + downloads upload via the v2.0 API.
@see  docs/playbook/git-hosts/bitbucket.md
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PlatformError, PublishError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, GitHost


class BitbucketCloud(GitHost):
    """
    Bitbucket Cloud (`bitbucket.org`).

    Config keys (under ``targets.bitbucket``)::

        "workspace":  "my-workspace"
        "repo":       "release-kit"
        "tag":        "v1.4.2"
        "username":   "my-bb-user"
        "env_var":    "BITBUCKET_APP_PASSWORD"
    """

    slug: ClassVar[str] = "bitbucket"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.BASIC, AuthMethod.TOKEN,
    )

    _api_base = "https://api.bitbucket.org/2.0"

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._workspace: str = str(extras.get("workspace", ""))
        self._repo: str = str(extras.get("repo", ""))
        self._tag: str = str(extras.get("tag", ""))
        self._username: str = str(extras.get("username", ""))
        self._env_var: str = str(extras.get("env_var", "BITBUCKET_APP_PASSWORD"))

    def _auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self._username, getattr(self, "_password", "") or "")

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._workspace or not self._repo:
            raise AuthenticationError(
                "bitbucket needs workspace + repo",
                code="missing-config",
            )
        if not self._username:
            raise AuthenticationError(
                "bitbucket.username not configured",
                code="missing-username",
            )
        resolution = resolve_token("bitbucket", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no Bitbucket app password resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._password = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"{self._workspace}/{self._repo} as {self._username}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._tag:
            raise AuthenticationError("bitbucket.tag not configured", code="missing-tag")
        return StepOutcome(step="validate", status="ok", detail=f"tag={self._tag}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        """
        Ensure the tag exists on Bitbucket.

        Bitbucket auto-imports git tags from the repo; this method
        confirms it's there + reports back. Asset uploads are
        deferred to future versions.
        """
        path = f"/repositories/{self._workspace}/{self._repo}/refs/tags/{self._tag}"
        if ctx.dry_run:
            return StepOutcome(
                step="publish", status="dry-run",
                detail=f"would verify tag {self._tag} on {self._workspace}/{self._repo}",
            )
        try:
            with httpx.Client(timeout=30.0, auth=self._auth()) as client:
                r = client.get(f"{self._api_base}{path}")
        except httpx.HTTPError as e:
            raise PublishError(f"Bitbucket API error: {e}", code="bitbucket-api-error") from e
        if r.status_code == 404:
            raise PublishError(
                f"tag {self._tag} not found; push the tag first",
                code="tag-not-pushed",
            )
        if not r.is_success:
            raise PlatformError(
                f"Bitbucket returned {r.status_code}: {r.text[:200]}",
                code="bitbucket-api-error",
            )
        return StepOutcome(step="publish", status="ok", detail=f"tag {self._tag} present")
