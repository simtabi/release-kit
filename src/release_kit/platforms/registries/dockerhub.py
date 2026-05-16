"""Docker Hub publisher.

@see  docs/playbook/registries/dockerhub.md
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, VerifyError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.docker_push import DockerPushMixin


class DockerHub(DockerPushMixin, Registry):
    """
    Docker Hub registry.

    Config keys (under ``targets.dockerhub``)::

        "username":  "my-dockerhub-user"
        "image":     "my-namespace/my-image"
        "tags":      ["latest", "${VERSION}"]
        "env_var":   "DOCKERHUB_TOKEN"
        "platforms": ["linux/amd64", "linux/arm64"]   # optional
    """

    slug: ClassVar[str] = "dockerhub"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._username: str = str(extras.get("username", ""))
        self._image: str = str(extras.get("image", ""))
        self._tags: list[str] = list(extras.get("tags") or ["latest"])
        self._env_var: str = str(extras.get("env_var", "DOCKERHUB_TOKEN"))
        self._platforms_cfg: list[str] = list(
            extras.get("platforms") or ["linux/amd64", "linux/arm64"]
        )

    @property
    def _platforms(self) -> list[str]:
        return self._platforms_cfg

    # ---- lifecycle ---------------------------------------------------

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._username:
            raise AuthenticationError(
                "dockerhub.username not configured",
                code="missing-username",
                remediation="Set targets.dockerhub.username in release.json.",
            )
        resolution = resolve_token("dockerhub", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no Docker Hub token resolved (env={self._env_var})",
                code="token-not-found",
                remediation=f"Set {self._env_var} via env, .env, or `keyring set release-kit dockerhub`.",
            )
        self._password = resolution.value
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"username={self._username}; token from {resolution.source}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._image:
            raise AuthenticationError(
                "dockerhub.image not configured",
                code="missing-image",
                remediation="Set targets.dockerhub.image = '<namespace>/<image>'.",
            )
        return StepOutcome(step="validate", status="ok", detail=f"image={self._image}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def reach_probe(self, ctx: RunContext) -> StepOutcome:
        """HEAD-probe hub.docker.com with a 5-second timeout."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.head("https://hub.docker.com/v2/", follow_redirects=True)
        except httpx.HTTPError as e:
            return StepOutcome(step="reach", status="failed", detail=f"unreachable: {e}")
        if r.status_code >= 500:
            return StepOutcome(
                step="reach", status="failed", detail=f"docker hub returned {r.status_code}"
            )
        return StepOutcome(
            step="reach", status="ok", detail=f"hub.docker.com -> {r.status_code}"
        )

    def verify(self, ctx: RunContext) -> StepOutcome:
        """Confirm at least one of the requested tags resolves via Docker Hub's v2 API."""
        if not self._image or "/" not in self._image:
            return StepOutcome(step="verify", status="skipped", detail="no image to verify")
        url = f"https://hub.docker.com/v2/repositories/{self._image}/tags/{self._tags[0]}/"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
        except httpx.HTTPError as e:
            raise VerifyError(f"network error verifying {url}: {e}", code="verify-network") from e
        if r.status_code == 200:
            return StepOutcome(
                step="verify", status="ok", detail=f"{self._image}:{self._tags[0]} live"
            )
        if r.status_code == 404:
            raise VerifyError(
                f"Docker Hub returned 404 for {self._image}:{self._tags[0]}",
                code="verify-not-found",
            )
        raise VerifyError(
            f"Docker Hub returned {r.status_code} for {url}",
            code="verify-bad-status",
        )

    # ---- mixin overrides ---------------------------------------------

    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        return [
            "docker",
            "login",
            "--username",
            self._username,
            "--password-stdin",
            # We can't pipe stdin through subprocess.run with a list easily;
            # callers should pre-stage `docker login` or use --password (with
            # the security caveat). For now, return the safe variant; in
            # practice CI uses docker/login-action.
            "registry-1.docker.io",
        ]

    def _image_reference(self, tag: str) -> str:
        return f"{self._image}:{tag}"

    def _default_tags(self, ctx: RunContext) -> list[str]:
        return self._tags
