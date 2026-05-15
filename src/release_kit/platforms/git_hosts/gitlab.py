"""GitLab.com publisher.

Creates GitLab release objects via REST v4.
@see  docs/playbook/git-hosts/gitlab.md
"""

from __future__ import annotations

from typing import ClassVar
from urllib.parse import quote

from ...core.errors import AuthenticationError, PublishError
from ...core.runner import RunContext, StepOutcome
from ..base import AuthMethod, AutomationLevel, GitHost
from ..mixins.gitlab_api import GitLabApiMixin


class GitLab(GitLabApiMixin, GitHost):
    """
    GitLab.com host.

    Config keys (under ``targets.gitlab``)::

        "project":       "my-group/release-kit"      # OR
        "project_id":    12345
        "tag":           "v1.4.2"
        "description":   "release notes here"
        "env_var":       "GITLAB_TOKEN"
    """

    slug: ClassVar[str] = "gitlab"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC,
        AuthMethod.TOKEN,
    )
    api_base: str = "https://gitlab.com"

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._project: str = str(extras.get("project", ""))
        self._project_id: int | None = extras.get("project_id")
        self._tag: str = str(extras.get("tag", ""))
        self._description: str = str(extras.get("description", ""))
        self._env_var: str = str(extras.get("env_var", "GITLAB_TOKEN"))

    def _project_path(self) -> str:
        if self._project_id is not None:
            return str(self._project_id)
        return quote(self._project, safe="")

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._project and not self._project_id:
            raise AuthenticationError(
                "gitlab needs project (path or numeric id)",
                code="missing-project",
                remediation="Set targets.gitlab.project or .project_id.",
            )
        with self._client(ctx, env_var=self._env_var):
            pass
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"project={self._project or self._project_id}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._tag:
            raise AuthenticationError(
                "gitlab.tag not configured",
                code="missing-tag",
            )
        return StepOutcome(step="validate", status="ok", detail=f"tag={self._tag}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        path = f"/projects/{self._project_path()}/releases"
        body: dict[str, object] = {
            "name": self._tag,
            "tag_name": self._tag,
            "description": self._description or self._tag,
        }
        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would POST {path} with tag={self._tag}",
            )
        try:
            self._api_post(ctx, path, body, env_var=self._env_var)
        except Exception as e:
            raise PublishError(
                f"failed to create GitLab release {self._tag}: {e}",
                code="gitlab-release-failed",
            ) from e
        return StepOutcome(
            step="publish",
            status="ok",
            detail=f"release {self._tag} created",
        )

    def verify(self, ctx: RunContext) -> StepOutcome:
        if ctx.dry_run:
            return StepOutcome(step="verify", status="skipped", detail="dry-run; skipped")
        try:
            body = self._api_get(
                ctx,
                f"/projects/{self._project_path()}/releases/{self._tag}",
                env_var=self._env_var,
            )
        except Exception:
            return StepOutcome(
                step="verify", status="failed", detail=f"release {self._tag} not found"
            )
        return StepOutcome(step="verify", status="ok", detail=f"name={body.get('name')}")
