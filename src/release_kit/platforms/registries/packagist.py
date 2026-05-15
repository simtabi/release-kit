"""Packagist publisher.

API-driven; doesn't host artefacts itself. Triggers an index refresh
via the Packagist update-package API after a tag is pushed.
@see  docs/playbook/registries/packagist.md
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PublishError, VerifyError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry


class Packagist(Registry):
    """
    Packagist (Composer PHP registry) refresh trigger.

    Config keys (under ``targets.packagist``)::

        "package":       "simtabi/release-kit"
        "username":      "my-packagist-user"
        "repository":    "https://github.com/simtabi/release-kit"
        "env_var":       "PACKAGIST_TOKEN"
    """

    slug: ClassVar[str] = "packagist"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    _api_base = "https://packagist.org/api"
    _info_base = "https://packagist.org/packages"

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._package: str = str(extras.get("package", ""))
        self._username: str = str(extras.get("username", ""))
        self._repo_url: str = str(extras.get("repository", ""))
        self._env_var: str = str(extras.get("env_var", "PACKAGIST_TOKEN"))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._package or "/" not in self._package:
            raise AuthenticationError(
                f"packagist.package must be '<vendor>/<name>' (got {self._package!r})",
                code="invalid-package",
            )
        if not self._username:
            raise AuthenticationError(
                "packagist.username not configured",
                code="missing-username",
            )
        resolution = resolve_token("packagist", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no Packagist token resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._token = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"package={self._package}; user={self._username}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._repo_url:
            raise AuthenticationError(
                "packagist.repository (git URL) not configured",
                code="missing-repo",
            )
        return StepOutcome(step="validate", status="ok", detail=f"repo={self._repo_url}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        """
        POST the update-package API to force a refresh.

        Packagist normally auto-refreshes via webhook; this is the
        fallback / explicit-trigger path.
        """
        url = f"{self._api_base}/update-package?username={self._username}&apiToken={getattr(self, '_token', '')}"
        body = {"repository": {"url": self._repo_url}}
        if ctx.dry_run:
            return StepOutcome(
                step="publish", status="dry-run",
                detail=f"would POST update-package for {self._package}",
            )
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(url, json=body)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise PublishError(
                f"Packagist update-package failed: {e}",
                code="packagist-update-failed",
            ) from e
        return StepOutcome(step="publish", status="ok", detail="refresh triggered")

    def verify(self, ctx: RunContext) -> StepOutcome:
        url = f"{self._info_base}/{self._package}.json"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
        except httpx.HTTPError as e:
            raise VerifyError(f"network error: {e}", code="verify-network") from e
        if r.status_code == 404:
            raise VerifyError(f"package not found: {self._package}", code="verify-not-found")
        if r.status_code != 200:
            raise VerifyError(f"Packagist returned {r.status_code}", code="verify-bad-status")
        versions = list((r.json().get("package", {}).get("versions", {}) or {}).keys())
        return StepOutcome(step="verify", status="ok", detail=f"{len(versions)} versions live")
