"""Azure DevOps Repos publisher.

Azure DevOps has no first-class "Release" object on Repos
(Releases live in a separate Pipelines feature). This class creates
a Git tag ref via the Repos REST API; that's the canonical release
artefact on Repos.
@see  docs/playbook/git-hosts/azure-devops.md
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PublishError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, GitHost


class AzureDevOps(GitHost):
    """
    Azure DevOps Repos host.

    Config keys (under ``targets.azure-devops``)::

        "organization":  "my-org"           # under dev.azure.com/<org>
        "project":       "my-project"
        "repo":          "release-kit"
        "tag":           "v1.4.2"
        "commit_sha":    "abc123..."        # what the tag points at
        "env_var":       "AZURE_DEVOPS_PAT"
    """

    slug: ClassVar[str] = "azure-devops"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._org: str = str(extras.get("organization", ""))
        self._project: str = str(extras.get("project", ""))
        self._repo: str = str(extras.get("repo", ""))
        self._tag: str = str(extras.get("tag", ""))
        self._sha: str = str(extras.get("commit_sha", ""))
        self._env_var: str = str(extras.get("env_var", "AZURE_DEVOPS_PAT"))

    def _api_base(self) -> str:
        return f"https://dev.azure.com/{self._org}/{self._project}/_apis/git"

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not all((self._org, self._project, self._repo)):
            raise AuthenticationError(
                "azure-devops needs organization + project + repo",
                code="missing-config",
            )
        resolution = resolve_token("azure-devops", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no Azure DevOps PAT resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._pat = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"{self._org}/{self._project}/{self._repo}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._tag:
            raise AuthenticationError("tag not configured", code="missing-tag")
        if not self._sha:
            raise AuthenticationError(
                "commit_sha required (Azure DevOps tag-ref needs the target SHA)",
                code="missing-sha",
            )
        return StepOutcome(step="validate", status="ok", detail=f"tag={self._tag} sha={self._sha[:12]}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        path = f"/repositories/{self._repo}/refs?api-version=7.1"
        body = [
            {
                "name": f"refs/tags/{self._tag}",
                "newObjectId": self._sha,
                "oldObjectId": "0000000000000000000000000000000000000000",
            }
        ]
        if ctx.dry_run:
            return StepOutcome(
                step="publish", status="dry-run",
                detail=f"would POST tag ref {self._tag} -> {self._sha[:12]}",
            )
        try:
            with httpx.Client(timeout=30.0, auth=("", self._pat or "")) as client:
                r = client.post(self._api_base() + path, json=body)
        except httpx.HTTPError as e:
            raise PublishError(f"network error: {e}", code="azure-devops-api-error") from e
        if not r.is_success:
            raise PublishError(
                f"Azure DevOps returned {r.status_code}: {r.text[:200]}",
                code="azure-devops-api-error",
            )
        return StepOutcome(step="publish", status="ok", detail=f"tag {self._tag} created")
