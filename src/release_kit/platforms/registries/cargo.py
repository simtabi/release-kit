"""crates.io (Cargo) publisher.

@see  docs/playbook/registries/cargo.md
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PublishError, VerifyError
from ...core.runner import RunContext, StepOutcome, run_command
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry


class CratesIo(Registry):
    """
    crates.io publisher.

    Config keys (under ``targets.cargo``)::

        "manifest_path": "Cargo.toml"
        "env_var":       "CARGO_REGISTRY_TOKEN"
        "crate_name":    "release-kit"
    """

    slug: ClassVar[str] = "cargo"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._manifest: str = str(extras.get("manifest_path", "Cargo.toml"))
        self._env_var: str = str(extras.get("env_var", "CARGO_REGISTRY_TOKEN"))
        self._crate_name: str = str(extras.get("crate_name", ""))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        resolution = resolve_token("cargo", env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no Cargo token resolved (env={self._env_var})",
                code="token-not-found",
            )
        self._token = resolution.value
        return StepOutcome(
            step="authenticate", status="ok", detail=f"token from {resolution.source}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not Path(self._manifest).is_file():
            raise AuthenticationError(
                f"{self._manifest} not found", code="no-manifest",
            )
        return StepOutcome(step="validate", status="ok", detail=self._manifest)

    def publish(self, ctx: RunContext) -> StepOutcome:
        argv = ["cargo", "publish", "--manifest-path", self._manifest]
        if ctx.dry_run:
            return StepOutcome(
                step="publish", status="dry-run",
                detail=f"would run: {' '.join(argv)} --dry-run",
            )
        try:
            run_command(
                argv,
                dry_run=False, check=True,
                env={"CARGO_REGISTRY_TOKEN": getattr(self, "_token", "")},
            )
        except Exception as e:
            raise PublishError(f"cargo publish failed: {e}", code="cargo-publish-failed") from e
        return StepOutcome(step="publish", status="ok", detail="cargo publish OK")

    def verify(self, ctx: RunContext) -> StepOutcome:
        if not self._crate_name:
            return StepOutcome(step="verify", status="skipped", detail="no crate_name configured")
        url = f"https://crates.io/api/v1/crates/{self._crate_name}"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url, headers={"User-Agent": "simtabi-release-kit"})
        except httpx.HTTPError as e:
            raise VerifyError(f"network error: {e}", code="verify-network") from e
        if r.status_code == 404:
            raise VerifyError(f"crate not found: {self._crate_name}", code="verify-not-found")
        if r.status_code != 200:
            raise VerifyError(f"crates.io returned {r.status_code}", code="verify-bad-status")
        return StepOutcome(
            step="verify", status="ok",
            detail=f"{self._crate_name}=={r.json().get('crate', {}).get('max_version')}",
        )
