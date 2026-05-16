"""GitHub Container Registry publisher.

@see  docs/playbook/registries/ghcr.md
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.docker_push import DockerPushMixin


class GHCR(DockerPushMixin, Registry):
    """
    GHCR registry (``ghcr.io``).

    Config keys (under ``targets.ghcr``)::

        "image": "ghcr.io/my-org/my-image"
        "tags":  ["latest", "${VERSION}"]
        "env_var": "GITHUB_TOKEN"        # or "GHCR_TOKEN"
        "github_actor": "my-user"        # github.actor in workflows
    """

    slug: ClassVar[str] = "ghcr"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC,
        AuthMethod.TOKEN,
    )

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._image: str = str(extras.get("image", ""))
        self._tags: list[str] = list(extras.get("tags") or ["latest"])
        self._env_var: str = str(extras.get("env_var", "GITHUB_TOKEN"))
        self._actor: str = str(extras.get("github_actor", ""))
        self._platforms_cfg: list[str] = list(
            extras.get("platforms") or ["linux/amd64", "linux/arm64"]
        )

    @property
    def _platforms(self) -> list[str]:
        return self._platforms_cfg

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._image:
            raise AuthenticationError(
                "ghcr.image not configured",
                code="missing-image",
                remediation="Set targets.ghcr.image = 'ghcr.io/<owner>/<repo>'.",
            )
        if not self._image.startswith("ghcr.io/"):
            raise AuthenticationError(
                f"ghcr.image must start with ghcr.io/ (got {self._image!r})",
                code="invalid-image",
            )
        resolution = resolve_token("ghcr", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no GHCR token resolved (env={self._env_var})",
                code="token-not-found",
                remediation=(
                    "In CI: use workflow GITHUB_TOKEN with permissions.packages: write.\n"
                    "Locally: set GHCR_TOKEN or GITHUB_TOKEN."
                ),
            )
        self._password = resolution.value
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"image={self._image}; token from {resolution.source}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        return StepOutcome(step="validate", status="ok", detail=f"image={self._image}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def reach_probe(self, ctx: RunContext) -> StepOutcome:
        """HEAD-probe ghcr.io with a 5-second timeout."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.head("https://ghcr.io/v2/", follow_redirects=True)
        except httpx.HTTPError as e:
            return StepOutcome(step="reach", status="failed", detail=f"unreachable: {e}")
        # GHCR returns 401 unauthenticated on /v2/, which still proves reach.
        if r.status_code >= 500:
            return StepOutcome(
                step="reach", status="failed", detail=f"ghcr returned {r.status_code}"
            )
        return StepOutcome(step="reach", status="ok", detail=f"ghcr.io -> {r.status_code}")

    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        # The actual `docker login` in CI is handled by docker/login-action;
        # locally users `echo $GHCR_TOKEN | docker login ghcr.io ...`.
        # We don't ship subprocess login here because piping stdin through
        # subprocess.run with the list-argv pattern adds little safety.
        return None

    def _image_reference(self, tag: str) -> str:
        return f"{self._image}:{tag}"

    def _default_tags(self, ctx: RunContext) -> list[str]:
        return self._tags
