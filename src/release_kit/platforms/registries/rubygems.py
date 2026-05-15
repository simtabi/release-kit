"""RubyGems publisher.

@see  docs/playbook/registries/rubygems.md
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PublishError, VerifyError
from ...core.runner import RunContext, StepOutcome, run_command
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry


class RubyGems(Registry):
    """
    RubyGems.org publisher.

    Config keys (under ``targets.rubygems``)::

        "gemspec":   "release-kit.gemspec"
        "env_var":   "RUBYGEMS_API_KEY"
    """

    slug: ClassVar[str] = "rubygems"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC, AuthMethod.TOKEN,
    )

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._gemspec: str = str(extras.get("gemspec", ""))
        self._env_var: str = str(extras.get("env_var", "RUBYGEMS_API_KEY"))
        self._gem_name: str = str(extras.get("gem_name", ""))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._gemspec:
            raise AuthenticationError(
                "rubygems.gemspec not configured",
                code="missing-gemspec",
                remediation="Set targets.rubygems.gemspec = '<name>.gemspec'.",
            )
        if self.target.auth == "oidc":
            return StepOutcome(step="authenticate", status="ok", detail="OIDC trusted publisher path")
        resolution = resolve_token("rubygems", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no RubyGems API key resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._api_key = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"api key from {resolution.source}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not Path(self._gemspec).is_file():
            raise AuthenticationError(
                f"{self._gemspec} not found",
                code="no-gemspec",
            )
        return StepOutcome(step="validate", status="ok", detail=f"gemspec={self._gemspec}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        build_argv = ["gem", "build", self._gemspec]
        if ctx.dry_run:
            return StepOutcome(
                step="publish", status="dry-run",
                detail=f"would build + push {self._gemspec}",
            )
        try:
            run_command(build_argv, dry_run=False, check=True)
            # find the built .gem
            built = sorted(Path().glob("*.gem"))
            if not built:
                raise PublishError("gem build produced no .gem file", code="gem-build-empty")
            run_command(["gem", "push", str(built[-1])], dry_run=False, check=True)
        except Exception as e:
            raise PublishError(f"gem push failed: {e}", code="gem-push-failed") from e
        return StepOutcome(step="publish", status="ok", detail=f"pushed {built[-1]}")

    def verify(self, ctx: RunContext) -> StepOutcome:
        if not self._gem_name:
            return StepOutcome(step="verify", status="skipped", detail="no gem_name configured")
        url = f"https://rubygems.org/api/v1/gems/{self._gem_name}.json"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
        except httpx.HTTPError as e:
            raise VerifyError(f"network error: {e}", code="verify-network") from e
        if r.status_code == 404:
            raise VerifyError(f"gem not found: {self._gem_name}", code="verify-not-found")
        if r.status_code != 200:
            raise VerifyError(f"rubygems API returned {r.status_code}", code="verify-bad-status")
        return StepOutcome(
            step="verify", status="ok",
            detail=f"{self._gem_name}=={r.json().get('version')}",
        )
