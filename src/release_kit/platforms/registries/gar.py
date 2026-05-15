"""Google Artifact Registry publisher.

@see  docs/playbook/registries/gar.md
"""

from __future__ import annotations

from typing import ClassVar

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.docker_push import DockerPushMixin


class GoogleArtifactRegistry(DockerPushMixin, Registry):
    """
    Google Artifact Registry (Docker format).

    Auth: ``gcloud auth configure-docker <region>-docker.pkg.dev`` is
    the canonical flow. In CI, Workload Identity Federation via
    ``google-github-actions/auth`` is preferred.

    Config keys (under ``targets.gar``)::

        "registry":   "us-central1-docker.pkg.dev"
        "project":    "my-gcp-project"
        "repo":       "my-repo"
        "image":      "release-kit"
        "tags":       ["latest", "${VERSION}"]
    """

    slug: ClassVar[str] = "gar"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.CLI_LOGIN
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.CLI,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._registry: str = str(extras.get("registry", ""))
        self._project: str = str(extras.get("project", ""))
        self._repo: str = str(extras.get("repo", ""))
        self._image: str = str(extras.get("image", ""))
        self._tags: list[str] = list(extras.get("tags") or ["latest"])
        self._platforms_cfg: list[str] = list(
            extras.get("platforms") or ["linux/amd64", "linux/arm64"]
        )

    @property
    def _platforms(self) -> list[str]:
        return self._platforms_cfg

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not all((self._registry, self._project, self._repo, self._image)):
            raise AuthenticationError(
                "gar requires registry + project + repo + image",
                code="missing-config",
                remediation=(
                    "Set targets.gar.registry, .project, .repo, .image. "
                    "Example: us-central1-docker.pkg.dev / my-project / my-repo / release-kit."
                ),
            )
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"registry={self._registry}; project={self._project}; auth via gcloud auth configure-docker",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        return StepOutcome(step="validate", status="ok", detail=f"repo={self._repo}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        return None  # gcloud auth handled out-of-band

    def _image_reference(self, tag: str) -> str:
        return f"{self._registry}/{self._project}/{self._repo}/{self._image}:{tag}"

    def _default_tags(self, ctx: RunContext) -> list[str]:
        return self._tags
