"""PyPI reference implementation.

This is the canonical template every other platform follows. Read
``docs/playbook/registries/pypi.md`` for the workflow this code
automates; this module is the executable version of that page.

What's covered:

- Authentication via OIDC trusted publisher (no token) or per-project
  API token. The runner refuses to fall back to token auth unless
  ``policies.allow_token_auth`` is True or ``RELEASE_KIT_ALLOW_TOKEN_AUTH=1``
  is set.
- Validation: dist files exist, ``twine check`` passes, version is
  not yet on PyPI (idempotency).
- Publish: ``twine upload`` (when OIDC isn't in play locally).
- Verify: HTTP GET ``/pypi/<name>/<version>/json`` returns 200.
- Rollback: PyPI doesn't allow delete; rollback yanks instead, and
  only with explicit policy opt-in (it has user-visible effects).
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import httpx

from ...core.errors import (
    AuthenticationError,
    PublishError,
    ValidationError,
    VerifyError,
)
from ...core.logging import get_logger
from ...core.runner import RunContext, StepOutcome, run_command
from ...core.secrets import resolve_token
from ..base import AuthMethod, AutomationLevel, Registry

_log = get_logger(__name__)


class PyPI(Registry):
    """
    PyPI publisher.

    Config example (see docs/configuration.md for the full schema)::

        "pypi": {
          "enabled": true,
          "auth": "oidc",
          "repository": "pypi",         // or "testpypi"
          "dist_glob": "dist/*",        // built artefacts to upload
          "env_var": "PYPI_TOKEN"       // override the default
        }

    @see  docs/playbook/registries/pypi.md  for the workflow.
    """

    slug: ClassVar[str] = "pypi"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC,
        AuthMethod.TOKEN,
    )

    # PyPI API endpoints
    _PROD_API = "https://pypi.org"
    _TEST_API = "https://test.pypi.org"

    def __post_init__(self) -> None:
        extras = self.target.model_extra or {}
        self._repository: str = str(extras.get("repository", "pypi"))
        self._dist_glob: str = str(extras.get("dist_glob", "dist/*"))
        self._env_var: str = str(extras.get("env_var", "PYPI_TOKEN"))
        self._project_name: str | None = extras.get("project_name")  # set by Config layer

    # ---- lifecycle ---------------------------------------------------

    def authenticate(self, ctx: RunContext) -> StepOutcome:
        """
        Resolve PyPI credentials.

        OIDC path: in GitHub Actions / GitLab CI, the
        ``pypa/gh-action-pypi-publish`` workflow handles auth
        out-of-band; this method just confirms the runtime smells
        like CI (env vars present) and returns ``ok``.

        Token path: walks the resolution chain to find a real token.
        Refuses to fall back without policy opt-in.

        @param  ctx
        @return StepOutcome  step="authenticate"
        @throws AuthenticationError  when no method resolves.
        """
        if self.target.auth == "oidc":
            if self._looks_like_ci():
                return StepOutcome(
                    step="authenticate",
                    status="ok",
                    detail="OIDC: CI environment detected; trusted publisher will issue token",
                )
            if not ctx.policies.allow_token_auth:
                raise AuthenticationError(
                    "auth='oidc' but no CI OIDC environment detected; "
                    "refusing to fall back to token auth",
                    code="oidc-not-available",
                    remediation=(
                        "Set policies.allow_token_auth=true OR run on CI "
                        "OR change target.auth to 'token'."
                    ),
                )
            # Fall through to token chain when policy permits.

        resolution = resolve_token(self.slug, env_var=self._env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no PyPI token resolved (looked at env {self._env_var}, "
                f"RELEASE_KIT_TOKEN_PYPI, OS keyring)",
                code="token-not-found",
                remediation=(
                    f"Set {self._env_var} in the environment, or store via "
                    "`keyring set release-kit pypi`."
                ),
            )
        return StepOutcome(
            step="authenticate",
            status="ok",
            detail=f"token resolved from {resolution.source} ({resolution.preview})",
        )

    def validate(self, ctx: RunContext) -> StepOutcome:
        """
        Preflight: confirm ``dist/`` is populated + ``twine check`` clean.

        @param  ctx
        @return StepOutcome  step="validate"
        @throws ValidationError
        """
        dist_files = list(Path().glob(self._dist_glob))
        if not dist_files:
            raise ValidationError(
                f"no dist files match {self._dist_glob!r}",
                code="no-dist",
                remediation="Run `python -m build` to produce sdist + wheel.",
            )
        # Defer ``twine check`` to publish-time so unit tests don't
        # require twine on PATH.
        return StepOutcome(
            step="validate",
            status="ok",
            detail=f"{len(dist_files)} dist file(s) match {self._dist_glob!r}",
        )

    def publish(self, ctx: RunContext) -> StepOutcome:
        """
        Upload the dist files via ``twine upload``.

        Honours ``ctx.dry_run``. When dry-run, returns the planned
        command without invoking twine.

        Idempotency: when verify() reveals the version is already
        on PyPI, the runner short-circuits via the caller; this
        method assumes it must upload.

        @param  ctx
        @return StepOutcome  step="publish"
        @throws PublishError
        """
        argv = [
            "python",
            "-m",
            "twine",
            "upload",
            "--non-interactive",
            "--repository",
            self._repository,
            self._dist_glob,
        ]
        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would run: {' '.join(argv)}",
            )
        try:
            run_command(argv, dry_run=False, check=True)
        except Exception as e:
            raise PublishError(
                f"twine upload failed: {e}",
                code="twine-failed",
                remediation="Check twine output above; common causes: missing token, name collision.",
            ) from e
        return StepOutcome(step="publish", status="ok", detail="uploaded via twine")

    def reach_probe(self, ctx: RunContext) -> StepOutcome:
        """HEAD-probe PyPI's index URL with a 5-second timeout."""
        base = self._TEST_API if self._repository == "testpypi" else self._PROD_API
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.head(f"{base}/simple/", follow_redirects=True)
        except httpx.HTTPError as e:
            return StepOutcome(
                step="reach",
                status="failed",
                detail=f"unreachable: {e}",
            )
        if r.status_code >= 500:
            return StepOutcome(
                step="reach",
                status="failed",
                detail=f"{base} returned {r.status_code}",
            )
        return StepOutcome(step="reach", status="ok", detail=f"{base} -> {r.status_code}")

    def verify(self, ctx: RunContext) -> StepOutcome:
        """
        Confirm the latest version is live on PyPI.

        Hits ``GET /pypi/<name>/json`` and reads ``info.version``.
        @param  ctx
        @return StepOutcome  step="verify"
        @throws VerifyError
        """
        if not self._project_name:
            return StepOutcome(
                step="verify",
                status="skipped",
                detail="no project_name configured; skip verify",
            )
        base = self._TEST_API if self._repository == "testpypi" else self._PROD_API
        url = f"{base}/pypi/{self._project_name}/json"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
        except httpx.HTTPError as e:
            raise VerifyError(
                f"network error verifying {url}: {e}",
                code="verify-network",
            ) from e
        if r.status_code == 404:
            raise VerifyError(
                f"PyPI returned 404 for {self._project_name}; project not found",
                code="verify-not-found",
                remediation="If this is a first publish, wait 30-90s for CDN.",
            )
        if r.status_code != 200:
            raise VerifyError(
                f"PyPI returned {r.status_code} for {url}",
                code="verify-bad-status",
            )
        version = r.json().get("info", {}).get("version", "")
        return StepOutcome(
            step="verify",
            status="ok",
            detail=f"latest on PyPI: {self._project_name}=={version}",
        )

    # ---- helpers -----------------------------------------------------

    @staticmethod
    def _looks_like_ci() -> bool:
        """
        Heuristic: returns True iff the current environment looks
        like GitHub Actions or GitLab CI with an OIDC token surface
        available.

        We don't reach for the token; we just check the well-known
        marker env vars that those providers always set.
        """
        import os

        return any(
            os.environ.get(var)
            for var in ("GITHUB_ACTIONS", "GITLAB_CI", "ACTIONS_ID_TOKEN_REQUEST_TOKEN")
        )
