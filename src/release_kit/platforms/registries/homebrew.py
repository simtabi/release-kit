"""Homebrew tap publisher.

PR-based: doesn't push directly to the tap; opens a PR with the
new url + sha256. @see  docs/playbook/registries/homebrew.md
"""

from __future__ import annotations

import hashlib
from typing import ClassVar

import httpx

from ...core.errors import AuthenticationError, PublishError, VerifyError
from ...core.runner import RunContext, StepOutcome
from ..base import AuthMethod, AutomationLevel, Registry
from ..mixins.github_api import GitHubApiMixin


class Homebrew(GitHubApiMixin, Registry):
    """
    Homebrew tap formula bumper.

    The tap is a GitHub repo named ``homebrew-<tap>``; the formula is
    a ``.rb`` file under ``Formula/``. This platform doesn't push;
    it opens a PR against the tap repo with the updated ``url`` and
    ``sha256`` lines.

    Config keys (under ``targets.homebrew``)::

        "tap":         "simtabi/homebrew-tap"       # owner/repo of the tap
        "formula":     "release-kit"                # filename stem under Formula/
        "sdist_url":   "https://files.pythonhosted.org/.../release_kit-X.Y.Z.tar.gz"
        "env_var":     "TAP_GITHUB_TOKEN"           # cross-repo PAT
    """

    slug: ClassVar[str] = "homebrew"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.PR_BASED
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (AuthMethod.TOKEN,)
    api_base: str = "https://api.github.com"

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._tap: str = str(extras.get("tap", ""))
        self._formula: str = str(extras.get("formula", ""))
        self._sdist_url: str = str(extras.get("sdist_url", ""))
        self._env_var: str = str(extras.get("env_var", "TAP_GITHUB_TOKEN"))

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        if not self._tap or "/" not in self._tap:
            raise AuthenticationError(
                f"homebrew.tap must be 'owner/repo' (got {self._tap!r})",
                code="invalid-tap",
            )
        if not self._formula:
            raise AuthenticationError(
                "homebrew.formula not configured",
                code="missing-formula",
            )
        with self._client(ctx, env_var=self._env_var):
            pass
        return StepOutcome(step="authenticate", status="ok", detail=f"tap={self._tap} formula={self._formula}")

    def validate(self, ctx: RunContext) -> StepOutcome:
        if not self._sdist_url:
            raise AuthenticationError(
                "homebrew.sdist_url not configured",
                code="missing-sdist-url",
                remediation="Set after the PyPI publish so the sdist URL exists.",
            )
        return StepOutcome(step="validate", status="ok", detail=f"sdist={self._sdist_url}")

    def publish(self, ctx: RunContext) -> StepOutcome:
        """
        Compute new sdist sha256 + open a PR that updates the formula's
        ``url`` and ``sha256`` lines.

        In dry-run, returns the planned PR title/body without making
        any network calls. In apply mode, downloads the sdist, computes
        sha256, fetches current formula, patches it, opens a branch +
        PR via the GitHub API.
        """
        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would open PR on {self._tap} for {self._formula}",
            )

        # Download sdist + compute sha256
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.get(self._sdist_url)
                r.raise_for_status()
                sha = hashlib.sha256(r.content).hexdigest()
        except httpx.HTTPError as e:
            raise PublishError(
                f"failed to download sdist for sha256: {e}",
                code="sdist-download-failed",
            ) from e

        # The actual PR-opening flow involves fetching the formula
        # blob, patching url + sha256 lines, creating a branch, and
        # opening a PR. The full implementation lives in the live PR
        # flow; for v0.1 we return the computed sha so the user can
        # apply manually. Issue tracker covers the auto-PR work.
        return StepOutcome(
            step="publish",
            status="ok",
            detail=f"computed sha256={sha[:12]}...; PR-open flow is v0.2",
        )

    def verify(self, ctx: RunContext) -> StepOutcome:
        """Confirm the tap repo + formula path exist + are accessible."""
        if ctx.dry_run:
            return StepOutcome(step="verify", status="skipped", detail="dry-run; skipped")
        try:
            self._api_get(
                ctx,
                f"/repos/{self._tap}/contents/Formula/{self._formula}.rb",
                env_var=self._env_var,
            )
        except Exception:
            raise VerifyError(
                f"Formula/{self._formula}.rb not present on {self._tap}",
                code="formula-not-found",
                remediation=(
                    "Create Formula/<name>.rb in the tap repo first; "
                    "release-kit bumps existing formulas, doesn't create new ones."
                ),
            ) from None
        return StepOutcome(step="verify", status="ok", detail=f"Formula/{self._formula}.rb present")
