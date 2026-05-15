"""AWS ECR (private or public) publisher.

@see  docs/playbook/registries/aws-ecr.md
"""

from __future__ import annotations

from typing import ClassVar

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.docker_push import DockerPushMixin


class AWSElasticContainerRegistry(DockerPushMixin, Registry):
    """
    AWS Elastic Container Registry.

    Auth flow: ``aws ecr get-login-password | docker login --password-stdin``.
    We can't pipe through ``run_command``'s argv-only model in a single
    call, so the mixin's ``_login_argv`` returns None and we publish
    a ``_pre_publish`` step that prints the user-facing instruction.
    In CI, the proper flow uses ``aws-actions/amazon-ecr-login@v2``.

    Config keys (under ``targets.aws-ecr``)::

        "registry":  "<account>.dkr.ecr.<region>.amazonaws.com"
        "image":     "release-kit"
        "region":    "us-east-1"
        "public":    false                          # use public ECR if true
        "tags":      ["latest", "${VERSION}"]
    """

    slug: ClassVar[str] = "aws-ecr"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.CLI_LOGIN
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.CLI,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._registry: str = str(extras.get("registry", ""))
        self._image: str = str(extras.get("image", ""))
        self._region: str = str(extras.get("region", "us-east-1"))
        self._public: bool = bool(extras.get("public", False))
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
                "aws-ecr.registry not configured",
                code="missing-registry",
                remediation="Set targets.aws-ecr.registry = '<account>.dkr.ecr.<region>.amazonaws.com'.",
            )
        if not self._image:
            raise AuthenticationError(
                "aws-ecr.image not configured",
                code="missing-image",
            )
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"registry={self._registry}; auth via aws ecr get-login-password",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        return StepOutcome(step="validate", status="ok", detail=f"region={self._region}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        """
        ``aws ecr get-login-password | docker login --password-stdin``
        is the canonical flow. We don't pipe via run_command's argv model;
        callers wire the login at the CI step level. Returning None lets
        the docker buildx step run after an already-logged-in session.
        """
        return None

    def _image_reference(self, tag: str) -> str:
        return f"{self._registry}/{self._image}:{tag}"

    def _default_tags(self, ctx: RunContext) -> list[str]:
        return self._tags
