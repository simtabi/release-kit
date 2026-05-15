"""NuGet.org publisher.

@see  docs/playbook/registries/nuget.md
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PublishError, VerifyError
from ...core.runner import RunContext, StepOutcome, run_command
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry


class NuGet(Registry):
    """
    NuGet.org publisher.

    Config keys (under ``targets.nuget``)::

        "package_glob":  "out/*.nupkg"
        "source":        "https://api.nuget.org/v3/index.json"
        "env_var":       "NUGET_API_KEY"
        "package_id":    "Simtabi.ReleaseKit"
    """

    slug: ClassVar[str] = "nuget"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._glob: str = str(extras.get("package_glob", "out/*.nupkg"))
        self._source: str = str(extras.get("source", "https://api.nuget.org/v3/index.json"))
        self._env_var: str = str(extras.get("env_var", "NUGET_API_KEY"))
        self._package_id: str = str(extras.get("package_id", ""))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        resolution = resolve_token("nuget", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no NuGet API key resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._api_key = resolution.value
        return StepOutcome(step="authenticate", status="ok", detail=f"key from {resolution.source}")

    def validate(self, ctx: RunContext) -> StepOutcome:
        pkgs = list(Path().glob(self._glob))
        if not pkgs:
            raise AuthenticationError(
                f"no .nupkg files match {self._glob!r}",
                code="no-packages",
                remediation="Run `dotnet pack -c Release -o out` to produce one.",
            )
        return StepOutcome(step="validate", status="ok", detail=f"{len(pkgs)} package(s)")

    def publish(self, ctx: RunContext) -> StepOutcome:
        argv = [
            "dotnet",
            "nuget",
            "push",
            self._glob,
            "--api-key",
            getattr(self, "_api_key", ""),
            "--source",
            self._source,
            "--skip-duplicate",
        ]
        if ctx.dry_run:
            # Redact the api-key in dry-run output
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would run: dotnet nuget push {self._glob} --source {self._source}",
            )
        try:
            run_command(argv, dry_run=False, check=True)
        except Exception as e:
            raise PublishError(f"dotnet nuget push failed: {e}", code="nuget-push-failed") from e
        return StepOutcome(step="publish", status="ok", detail=f"pushed {self._glob}")

    def verify(self, ctx: RunContext) -> StepOutcome:
        if not self._package_id:
            return StepOutcome(step="verify", status="skipped", detail="no package_id configured")
        url = f"https://api.nuget.org/v3-flatcontainer/{self._package_id.lower()}/index.json"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
        except httpx.HTTPError as e:
            raise VerifyError(f"network error: {e}", code="verify-network") from e
        if r.status_code == 404:
            raise VerifyError(f"package not found: {self._package_id}", code="verify-not-found")
        if r.status_code != 200:
            raise VerifyError(f"NuGet returned {r.status_code}", code="verify-bad-status")
        versions = r.json().get("versions", [])
        latest = versions[-1] if versions else "?"
        return StepOutcome(step="verify", status="ok", detail=f"{self._package_id}=={latest}")
