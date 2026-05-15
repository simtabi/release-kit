"""Docker push mixin.

Used by every OCI / Docker-protocol registry: Docker Hub, GHCR,
GitLab Container Registry, AWS ECR, Google Artifact Registry,
Azure Container Registry. Each subclass overrides the login flow
and the image reference computation; everything else is shared.
"""

from __future__ import annotations

from abc import abstractmethod

from ...core.errors import PublishError, ValidationError
from ...core.runner import RunContext, StepOutcome, run_command


class DockerPushMixin:
    """
    Shared docker-push flow.

    Subclasses must implement:

    - ``_login_argv(ctx)``         returns argv for ``docker login`` (or None if not needed)
    - ``_image_reference(tag)``    returns the full ``host/ns/image:tag``
    - ``_default_tags(ctx)``       returns the list of tags to build for

    Then the mixin's :py:meth:`publish` runs:

    1. login (if returned)
    2. buildx build --push --platform ... --tag ... --tag ... .

    Honours ``ctx.dry_run`` strictly.
    """

    # ---- abstract surface ------------------------------------------------

    @abstractmethod
    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        """Return argv for the registry's docker login. ``None`` means skip."""

    @abstractmethod
    def _image_reference(self, tag: str) -> str:
        """Compose the fully-qualified image reference for one tag."""

    @abstractmethod
    def _default_tags(self, ctx: RunContext) -> list[str]:
        """Tags to attach during the build."""

    @property
    def _platforms(self) -> list[str]:
        """Docker platforms to build for. Override in subclasses if needed."""
        return ["linux/amd64", "linux/arm64"]

    @property
    def _dockerfile(self) -> str:
        """Path to the Dockerfile. Override per subclass via config."""
        return "Dockerfile"

    @property
    def _context(self) -> str:
        """Build context dir."""
        return "."

    # ---- shared flow -----------------------------------------------------

    def _do_publish(self, ctx: RunContext) -> StepOutcome:
        """
        Run the docker login (if needed) + buildx build --push.

        @param  ctx
        @return StepOutcome  step="publish"
        @throws PublishError on any step's failure.
        @throws ValidationError when no tags were resolved.
        """
        tags = self._default_tags(ctx)
        if not tags:
            raise ValidationError(
                "no docker tags resolved; refusing to push without a tag",
                code="no-tags",
                remediation="Set targets.<name>.tags or pass --tag.",
            )

        login_argv = self._login_argv(ctx)
        if login_argv:
            try:
                run_command(login_argv, dry_run=ctx.dry_run, check=True)
            except Exception as e:
                raise PublishError(
                    f"docker login failed: {e}",
                    code="docker-login-failed",
                ) from e

        build_argv: list[str] = [
            "docker",
            "buildx",
            "build",
            "--platform",
            ",".join(self._platforms),
            "--push",
            "--file",
            self._dockerfile,
        ]
        for tag in tags:
            build_argv.extend(["--tag", self._image_reference(tag)])
        build_argv.append(self._context)

        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would build {len(tags)} tag(s) for {len(self._platforms)} platform(s)",
            )

        try:
            run_command(build_argv, dry_run=False, check=True)
        except Exception as e:
            raise PublishError(
                f"docker buildx build failed: {e}",
                code="docker-build-failed",
            ) from e
        return StepOutcome(
            step="publish",
            status="ok",
            detail=f"pushed {len(tags)} tag(s) for {len(self._platforms)} platform(s)",
        )
