"""Maven Central publisher (Central Portal path).

@see  docs/playbook/registries/maven-central.md
"""

from __future__ import annotations

from typing import ClassVar

from ...core.errors import AuthenticationError, PublishError
from ...core.runner import RunContext, StepOutcome, run_command
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry


class MavenCentral(Registry):
    """
    Maven Central publisher via Central Portal API.

    Drives ``./gradlew publishToMavenCentral`` (or ``mvn deploy``);
    we don't reimplement the GPG signing dance that Central requires.
    Caller must have GPG configured (see playbook).

    Config keys (under ``targets.maven-central``)::

        "build_tool":   "gradle"           # or "maven"
        "task":         "publishToMavenCentral"
        "user_env":     "CENTRAL_TOKEN_USER"
        "token_env":    "CENTRAL_TOKEN_VALUE"
    """

    slug: ClassVar[str] = "maven-central"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._build_tool: str = str(extras.get("build_tool", "gradle"))
        self._task: str = str(extras.get("task", "publishToMavenCentral"))
        self._user_env: str = str(extras.get("user_env", "CENTRAL_TOKEN_USER"))
        self._token_env: str = str(extras.get("token_env", "CENTRAL_TOKEN_VALUE"))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        user_res = resolve_token("maven-central-user", env_var=self._user_env)
        token_res = resolve_token("maven-central-token", env_var=self._token_env)
        if not user_res.resolved or not token_res.resolved:
            raise AuthenticationError(
                f"need both {self._user_env} (user) and {self._token_env} (token)",
                code="token-not-found",
                remediation="Generate a Central Portal API token at central.sonatype.com.",
            )
        self._user = user_res.value
        self._token = token_res.value
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"user={user_res.source} token={token_res.source}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if self._build_tool not in {"gradle", "maven"}:
            raise AuthenticationError(
                f"build_tool must be 'gradle' or 'maven' (got {self._build_tool!r})",
                code="invalid-build-tool",
            )
        return StepOutcome(step="validate", status="ok", detail=f"build_tool={self._build_tool}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        if self._build_tool == "gradle":
            argv = ["./gradlew", self._task]
        else:
            argv = ["mvn", "deploy", "-DskipTests"]

        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would run: {' '.join(argv)}",
            )
        try:
            run_command(
                argv,
                dry_run=False,
                check=True,
                timeout=900.0,
                env={
                    "ORG_GRADLE_PROJECT_mavenCentralUsername": getattr(self, "_user", "") or "",
                    "ORG_GRADLE_PROJECT_mavenCentralPassword": getattr(self, "_token", "") or "",
                },
            )
        except Exception as e:
            raise PublishError(f"maven deploy failed: {e}", code="maven-deploy-failed") from e
        return StepOutcome(step="publish", status="ok", detail=f"{self._build_tool} publish OK")
