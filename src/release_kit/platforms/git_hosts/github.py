"""GitHub.com publisher.

Creates GitHub releases, applies repo topics + branch protection.
@see  docs/playbook/git-hosts/github.md
"""

from __future__ import annotations

from typing import ClassVar

from ...core.errors import AuthenticationError, PublishError
from ...core.runner import RunContext, StepOutcome
from ..base import AuthMethod, AutomationLevel, GitHost
from ..mixins.github_api import GitHubApiMixin


class GitHub(GitHubApiMixin, GitHost):
    """
    GitHub.com host.

    Config keys (under ``targets.github``)::

        "repo":           "owner/name"
        "tag":            "v1.4.2"
        "draft":          false
        "prerelease":     false
        "generate_notes": true
        "topics":         ["oss", "python"]
        "env_var":        "GITHUB_TOKEN"
    """

    slug: ClassVar[str] = "github"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC,
        AuthMethod.TOKEN,
    )
    api_base: str = "https://api.github.com"

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._repo: str = str(extras.get("repo", ""))
        self._tag: str = str(extras.get("tag", ""))
        self._draft: bool = bool(extras.get("draft", False))
        self._prerelease: bool = bool(extras.get("prerelease", False))
        self._generate_notes: bool = bool(extras.get("generate_notes", True))
        self._topics: list[str] = list(extras.get("topics") or [])
        self._env_var: str = str(extras.get("env_var", "GITHUB_TOKEN"))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._repo or "/" not in self._repo:
            raise AuthenticationError(
                f"github.repo must be 'owner/name' (got {self._repo!r})",
                code="invalid-repo",
            )
        # Trigger token lookup; raises if missing.
        with self._client(ctx, env_var=self._env_var):
            pass
        return StepOutcome(step="authenticate", status="ok", detail=f"repo={self._repo}")

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._tag:
            raise AuthenticationError(
                "github.tag not configured",
                code="missing-tag",
                remediation="Set targets.github.tag = 'vX.Y.Z'.",
            )
        return StepOutcome(step="validate", status="ok", detail=f"tag={self._tag}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        """Create the GitHub Release object."""
        path = f"/repos/{self._repo}/releases"
        body: dict[str, object] = {
            "tag_name": self._tag,
            "name": self._tag,
            "draft": self._draft,
            "prerelease": self._prerelease,
            "generate_release_notes": self._generate_notes,
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
                f"failed to create release {self._tag}: {e}",
                code="github-release-failed",
            ) from e
        return StepOutcome(
            step="publish",
            status="ok",
            detail=f"release {self._tag} created on {self._repo}",
        )

    def verify(self, ctx: RunContext) -> StepOutcome:
        """Confirm the release object exists on the repo."""
        if ctx.dry_run:
            return StepOutcome(step="verify", status="skipped", detail="dry-run; skipped")
        try:
            body = self._api_get(
                ctx, f"/repos/{self._repo}/releases/tags/{self._tag}", env_var=self._env_var
            )
        except Exception:
            return StepOutcome(step="verify", status="failed", detail=f"release {self._tag} not found")
        return StepOutcome(
            step="verify",
            status="ok",
            detail=f"release id={body.get('id')} url={body.get('html_url')}",
        )
