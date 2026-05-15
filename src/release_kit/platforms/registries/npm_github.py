"""npm via GitHub Packages publisher.

@see  docs/playbook/registries/npm-github.md
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.npm_publish import NpmPublishMixin


class NpmGitHubPackages(NpmPublishMixin, Registry):
    """
    npm packages hosted on GitHub Packages.

    Scoped names only: ``@<owner>/<pkg>``. Workflow ``GITHUB_TOKEN``
    with ``packages: write`` permission is sufficient in CI; PAT
    elsewhere.

    Config keys (under ``targets.npm-github``)::

        "package_dir": "."
        "scope":       "@simtabi"
        "env_var":     "GITHUB_TOKEN"
    """

    slug: ClassVar[str] = "npm-github"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._dir = Path(str(extras.get("package_dir", ".")))
        self._scope: str = str(extras.get("scope", ""))
        self._env_var: str = str(extras.get("env_var", "GITHUB_TOKEN"))

    @property
    def _package_dir(self) -> Path:
        return self._dir

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._scope or not self._scope.startswith("@"):
            raise AuthenticationError(
                "npm-github.scope must be '@<owner>'",
                code="missing-scope",
            )
        resolution = resolve_token("npm-github", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no token resolved (env={self._env_var})",
                code="token-not-found",
                remediation="In CI use GITHUB_TOKEN with permissions.packages: write.",
            )
        self._token = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"scope={self._scope}; token from {resolution.source}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        pj = self._dir / "package.json"
        if not pj.is_file():
            raise AuthenticationError(
                f"package.json not found at {pj}", code="no-package-json"
            )
        return StepOutcome(step="validate", status="ok", detail=str(pj))

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def _npmrc_lines(self, ctx: RunContext) -> list[str]:
        token = getattr(self, "_token", None) or ""
        return [
            f"{self._scope}:registry=https://npm.pkg.github.com",
            f"//npm.pkg.github.com/:_authToken={token}",
        ]

    def _publish_args(self, ctx: RunContext) -> list[str]:
        return []
