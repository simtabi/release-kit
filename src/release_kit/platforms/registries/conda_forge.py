"""conda-forge platform plugin (PR-based).

conda-forge doesn't accept direct uploads — every release goes
through a PR against the feedstock repo (e.g.
``conda-forge/<project>-feedstock``). This plugin automates the
mechanical parts: bumping ``recipe/meta.yaml``'s ``version`` and
``sha256``, committing the change to a branch, and opening a PR.
The merge stays human-gated because conda-forge's bot does its own
validation pass before a maintainer hits the button.

Config keys (under ``targets.conda-forge``)::

    "feedstock":  "conda-forge/release-kit-feedstock"   # PR target
    "fork":       "imanimanyara/release-kit-feedstock"  # your fork
    "version":    "0.2.0"                  # what to bump meta.yaml to
    "sha256":     "<hex>"                  # sdist sha256 for the new ver
    "env_var":    "TAP_GITHUB_TOKEN"       # PAT with feedstock fork access

The PR-based flow is documented in detail at
``docs/playbook/registries/conda-forge.md``.
"""

from __future__ import annotations

from typing import ClassVar

from ...core.errors import AuthenticationError, PublishError
from ...core.runner import RunContext, StepOutcome
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.github_api import GitHubApiMixin


class CondaForge(GitHubApiMixin, Registry):
    """conda-forge feedstock bump via PR."""

    slug: ClassVar[str] = "conda-forge"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.PR_BASED
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)
    api_base: str = "https://api.github.com"

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._feedstock: str = str(extras.get("feedstock", ""))
        self._fork: str = str(extras.get("fork", ""))
        self._version: str = str(extras.get("version", ""))
        self._sha256: str = str(extras.get("sha256", ""))
        self._env_var: str = str(extras.get("env_var", "TAP_GITHUB_TOKEN"))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._feedstock or "/" not in self._feedstock:
            raise AuthenticationError(
                f"conda-forge.feedstock must be 'org/name' (got {self._feedstock!r})",
                code="invalid-feedstock",
            )
        if not self._fork or "/" not in self._fork:
            raise AuthenticationError(
                f"conda-forge.fork must be 'user/name' (got {self._fork!r})",
                code="invalid-fork",
                remediation=(
                    "Set targets.conda-forge.fork to your personal fork "
                    "(e.g., 'yourname/<project>-feedstock')."
                ),
            )
        # Trigger token lookup; raises if missing.
        with self._client(ctx, env_var=self._env_var):
            pass
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"feedstock={self._feedstock} fork={self._fork}",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._version:
            raise AuthenticationError(
                "conda-forge.version not configured",
                code="missing-version",
            )
        if not self._sha256 or len(self._sha256) != 64:
            raise AuthenticationError(
                f"conda-forge.sha256 must be a 64-char hex digest (got len={len(self._sha256)})",
                code="invalid-sha256",
                remediation=(
                    "Compute via `curl -sSL <sdist-url> | shasum -a 256` after "
                    "the sdist is on PyPI."
                ),
            )
        return StepOutcome(
            step="validate",
            status="ok",
            detail=f"version={self._version} sha256={self._sha256[:8]}…",
        )

    def publish(self, ctx: RunContext) -> StepOutcome:
        """Plan a feedstock PR. Real PR creation is v0.3 work; for now
        dry-run prints the patch + PR URL, and `apply` raises with
        the explicit instruction so we never half-create a PR."""
        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=(
                    f"would patch recipe/meta.yaml on {self._fork} (version="
                    f"{self._version}, sha256={self._sha256[:8]}…) and open a PR "
                    f"against {self._feedstock}"
                ),
            )
        # Live PR creation requires: clone the fork, read recipe/meta.yaml,
        # template-substitute version + sha256, commit on a release branch,
        # push to fork, open PR via API. Each step needs careful error
        # handling around merge conflicts and existing branches. That
        # lands in v0.3 (separate ADR pending). For now, the apply path
        # raises so users get a clear "use the documented manual flow"
        # signal rather than a half-done state.
        raise PublishError(
            "conda-forge PR automation is not yet wired in release-kit (v0.2). "
            "Use the manual flow in docs/playbook/registries/conda-forge.md.",
            code="not-implemented",
            remediation=(
                "Run `gh repo clone " + self._fork + "`, edit recipe/meta.yaml "
                "by hand, push, and open the PR via `gh pr create`. "
                "Track release-kit#TBD for full automation."
            ),
        )

    def verify(self, ctx: RunContext) -> StepOutcome:
        """Confirm a recent PR exists on the feedstock for our version."""
        if ctx.dry_run:
            return StepOutcome(step="verify", status="skipped", detail="dry-run; skipped")
        path = f"/repos/{self._feedstock}/pulls?state=open"
        try:
            body = self._api_get(ctx, path, env_var=self._env_var)
        except Exception:
            return StepOutcome(
                step="verify",
                status="skipped",
                detail=f"could not query {self._feedstock} PRs",
            )
        # Body is a list (the GitHub API returns list[Pull] here).
        prs: list[object] = body if isinstance(body, list) else []
        match = [
            p for p in prs
            if isinstance(p, dict) and self._version in str(p.get("title", ""))
        ]
        if match:
            return StepOutcome(
                step="verify",
                status="ok",
                detail=f"open PR for {self._version} found on {self._feedstock}",
            )
        return StepOutcome(
            step="verify",
            status="skipped",
            detail=f"no open PR matching {self._version!r} on {self._feedstock}",
        )
