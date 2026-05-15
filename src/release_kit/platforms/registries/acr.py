"""Azure Container Registry publisher.

@see  docs/playbook/registries/acr.md
"""

from __future__ import annotations

from typing import ClassVar

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.docker_push import DockerPushMixin


class AzureContainerRegistry(DockerPushMixin, Registry):
    """
    Azure Container Registry.

    Auth: ``az acr login --name <registry>``. In CI, prefer Workload
    Identity Federation via ``azure/login@v2`` so no SP secret is
    stored.

    Config keys (under ``targets.acr``)::

        "registry":  "myreg"             # the ACR name; full host is myreg.azurecr.io
        "image":     "release-kit"
        "tags":      ["latest", "${VERSION}"]
    """

    slug: ClassVar[str] = "acr"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.CLI_LOGIN
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.CLI,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._registry: str = str(extras.get("registry", ""))
        self._image: str = str(extras.get("image", ""))
        self._tags: list[str] = list(extras.get("tags") or ["latest"])
        self._platforms_cfg: list[str] = list(
            extras.get("platforms") or ["linux/amd64", "linux/arm64"]
        )

    @property
    def _platforms(self) -> list[str]:
        return self._platforms_cfg

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._registry:
            raise AuthenticationError(
                "acr.registry not configured (the ACR name, not the full host)",
                code="missing-registry",
            )
        if not self._image:
            raise AuthenticationError(
                "acr.image not configured",
                code="missing-image",
            )
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"registry={self._registry}.azurecr.io; auth via az acr login",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        return StepOutcome(step="validate", status="ok", detail=f"image={self._image}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        # Could shell to `az acr login` here, but the canonical CI flow
        # uses azure/login@v2 + az acr login. Out-of-band.
        return None

    def _image_reference(self, tag: str) -> str:
        return f"{self._registry}.azurecr.io/{self._image}:{tag}"

    def _default_tags(self, ctx: RunContext) -> list[str]:
        return self._tags
