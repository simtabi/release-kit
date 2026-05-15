"""GitLab Container Registry publisher.

@see  docs/playbook/registries/gitlab-registry.md
"""

from __future__ import annotations

from typing import ClassVar

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.docker_push import DockerPushMixin


class GitLabRegistry(DockerPushMixin, Registry):
    """
    GitLab Container Registry (``registry.gitlab.com`` or self-managed).

    Config keys (under ``targets.gitlab-registry``)::

        "registry":  "registry.gitlab.com"
        "image":     "registry.gitlab.com/group/project"
        "tags":      ["latest", "${VERSION}"]
        "env_var":   "GITLAB_REGISTRY_TOKEN"
    """

    slug: ClassVar[str] = "gitlab-registry"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._registry: str = str(extras.get("registry", "registry.gitlab.com"))
        self._image: str = str(extras.get("image", ""))
        self._tags: list[str] = list(extras.get("tags") or ["latest"])
        self._env_var: str = str(extras.get("env_var", "GITLAB_REGISTRY_TOKEN"))
        self._platforms_cfg: list[str] = list(
            extras.get("platforms") or ["linux/amd64", "linux/arm64"]
        )

    @property
    def _platforms(self) -> list[str]:
        return self._platforms_cfg

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._image:
            raise AuthenticationError(
                "gitlab-registry.image not configured",
                code="missing-image",
                remediation="Set targets.gitlab-registry.image = 'registry.gitlab.com/<group>/<project>'.",
            )
        resolution = resolve_token("gitlab-registry", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no GitLab registry token resolved (env={self._env_var})",
                code="token-not-found",
                remediation=(
                    "In GitLab CI: CI_JOB_TOKEN is auto-injected.\n"
                    f"Externally: set {self._env_var} to a Deploy Token with write_registry."
                ),
            )
        self._token = resolution.value
        return StepOutcome(
            step="authenticate", status="ok",
            detail=f"registry={self._registry}; token from {resolution.source}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        return StepOutcome(step="validate", status="ok", detail=f"image={self._image}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        return None  # CI uses CI_JOB_TOKEN; local docker login is out-of-band

    def _image_reference(self, tag: str) -> str:
        return f"{self._image}:{tag}"

    def _default_tags(self, ctx: RunContext) -> list[str]:
        return self._tags
