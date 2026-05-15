"""npm via GitLab Package Registry publisher.

@see  docs/playbook/registries/npm-gitlab.md
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.npm_publish import NpmPublishMixin


class NpmGitLabRegistry(NpmPublishMixin, Registry):
    """
    npm packages hosted on a GitLab project's Package Registry.

    Config keys (under ``targets.npm-gitlab``)::

        "package_dir": "."
        "scope":       "@simtabi"
        "project_id":  12345
        "host":        "gitlab.com"     # or self-managed
        "env_var":     "GITLAB_NPM_TOKEN"
    """

    slug: ClassVar[str] = "npm-gitlab"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._dir = Path(str(extras.get("package_dir", ".")))
        self._scope: str = str(extras.get("scope", ""))
        self._project_id: int | None = extras.get("project_id")
        self._host: str = str(extras.get("host", "gitlab.com"))
        self._env_var: str = str(extras.get("env_var", "GITLAB_NPM_TOKEN"))

    @property
    def _package_dir(self) -> Path:
        return self._dir

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._scope or not self._scope.startswith("@"):
            raise AuthenticationError(
                "npm-gitlab.scope must be '@<group>'", code="missing-scope"
            )
        if not self._project_id:
            raise AuthenticationError(
                "npm-gitlab.project_id required (numeric GitLab project ID)",
                code="missing-project-id",
            )
        resolution = resolve_token("npm-gitlab", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no token resolved (env={self._env_var})",
                code="token-not-found",
                remediation="In CI: CI_JOB_TOKEN. Externally: a Deploy Token with write_package_registry.",
            )
        self._token = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"scope={self._scope}; project={self._project_id}; host={self._host}",
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
        reg = f"https://{self._host}/api/v4/projects/{self._project_id}/packages/npm/"
        return [
            f"{self._scope}:registry={reg}",
            f"//{self._host}/api/v4/projects/{self._project_id}/packages/npm/:_authToken={token}",
        ]

    def _publish_args(self, ctx: RunContext) -> list[str]:
        return []
