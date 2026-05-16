"""npm (registry.npmjs.org) publisher.

@see  docs/playbook/registries/npm.md
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError
from ...core.runner import RunContext, StepOutcome
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.npm_publish import NpmPublishMixin


class Npm(NpmPublishMixin, Registry):
    """
    Public npmjs.org registry.

    Config keys (under ``targets.npm``)::

        "package_dir": "."              # where package.json lives
        "access":      "public"         # or "restricted"
        "provenance":  true             # GitHub Actions OIDC provenance
        "env_var":     "NPM_TOKEN"
    """

    slug: ClassVar[str] = "npm"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC,
        AuthMethod.TOKEN,
    )

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._dir = Path(str(extras.get("package_dir", ".")))
        self._access: str = str(extras.get("access", "public"))
        self._provenance: bool = bool(extras.get("provenance", False))
        self._env_var: str = str(extras.get("env_var", "NPM_TOKEN"))

    @property
    def _package_dir(self) -> Path:
        return self._dir

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        resolution = resolve_token("npm", env_var=self._env_var)
        if not resolution.resolved:
            if self._provenance:
                # Provenance requires OIDC + a publish token (auto-issued in CI by setup-node).
                return StepOutcome(
                    step="authenticate",
                    status="ok",
                    detail="OIDC + provenance expected; setup-node will issue NODE_AUTH_TOKEN",
                )
            raise AuthenticationError(
                f"no npm token resolved (env={self._env_var})",
                code="token-not-found",
                remediation=f"Set {self._env_var} or use `npm login` to populate ~/.npmrc.",
            )
        self._token = resolution.value
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"token from {resolution.source}; access={self._access}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        pj = self._dir / "package.json"
        if not pj.is_file():
            raise AuthenticationError(
                f"package.json not found at {pj}",
                code="no-package-json",
                remediation="Set targets.npm.package_dir to the dir containing package.json.",
            )
        return StepOutcome(step="validate", status="ok", detail=f"package.json at {pj}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        return self._do_publish(ctx)

    def _npmrc_lines(self, ctx: RunContext) -> list[str]:
        token = getattr(self, "_token", None)
        if not token:
            return []
        return [f"//registry.npmjs.org/:_authToken={token}"]

    def _publish_args(self, ctx: RunContext) -> list[str]:
        args = ["--access", self._access]
        if self._provenance:
            args.append("--provenance")
        return args

    def reach_probe(self, ctx: RunContext) -> StepOutcome:
        """HEAD-probe registry.npmjs.org with a 5-second timeout."""
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.head("https://registry.npmjs.org/", follow_redirects=True)
        except httpx.HTTPError as e:
            return StepOutcome(step="reach", status="failed", detail=f"unreachable: {e}")
        if r.status_code >= 500:
            return StepOutcome(
                step="reach", status="failed", detail=f"npmjs returned {r.status_code}"
            )
        return StepOutcome(
            step="reach", status="ok", detail=f"registry.npmjs.org -> {r.status_code}"
        )
