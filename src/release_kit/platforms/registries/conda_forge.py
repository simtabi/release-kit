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
        """Create the feedstock PR.

        Flow:
        1. Clone the fork into a temp dir.
        2. Patch ``recipe/meta.yaml``: bump ``{% set version = "..." %}``
           and ``sha256: ...`` to the configured values.
        3. Commit on a release branch named
           ``release-kit/bump-<version>``.
        4. Push the branch to the fork.
        5. Open a PR against the feedstock via the GitHub API.

        Idempotent: if the branch + PR already exist for this version,
        we skip and return the existing PR's URL.

        @raises PublishError on git / API failure.
        """
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

        import re
        import subprocess
        import tempfile
        from pathlib import Path

        branch = f"release-kit/bump-{self._version}"
        fork_url = f"https://github.com/{self._fork}.git"

        with tempfile.TemporaryDirectory(prefix="release-kit-feedstock-") as tmp:
            tmp_path = Path(tmp)

            # 1. Clone the fork (shallow, --branch main).
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", fork_url, str(tmp_path / "feedstock")],
                    capture_output=True, text=True, check=True, timeout=120,
                )
            except subprocess.CalledProcessError as e:
                raise PublishError(
                    f"git clone {fork_url} failed: {e.stderr.strip()[:200]}",
                    code="clone-failed",
                ) from e
            repo_root = tmp_path / "feedstock"
            recipe = repo_root / "recipe" / "meta.yaml"
            if not recipe.is_file():
                raise PublishError(
                    f"recipe/meta.yaml not found in {self._fork}",
                    code="missing-recipe",
                    remediation=f"Confirm {self._fork} is a conda-forge feedstock fork.",
                )

            # 2. Patch version + sha256 + reset build number to 0.
            text = recipe.read_text(encoding="utf-8")
            new_text = re.sub(
                r'(\{\%\s*set\s+version\s*=\s*")[^"]+(".*\%\})',
                rf"\g<1>{self._version}\g<2>",
                text,
            )
            new_text = re.sub(
                r"(sha256:\s*)[0-9a-fA-F]{64}",
                rf"\g<1>{self._sha256}",
                new_text,
            )
            new_text = re.sub(
                r"(number:\s*)\d+",
                r"\g<1>0",
                new_text,
                count=1,
            )
            if new_text == text:
                raise PublishError(
                    f"recipe/meta.yaml patch was a no-op: nothing matched the "
                    f"version + sha256 + build-number regexes in {recipe}",
                    code="patch-no-op",
                    remediation=(
                        "Inspect recipe/meta.yaml in the fork. The expected "
                        'patterns are `{% set version = "X.Y.Z" %}`, '
                        "`sha256: <64-hex>`, and `number: <int>`."
                    ),
                )
            recipe.write_text(new_text, encoding="utf-8")

            # 3. Create a release branch + commit.
            def _git(*args: str) -> str:
                r = subprocess.run(
                    ["git", *args],
                    capture_output=True, text=True, cwd=repo_root, timeout=60,
                )
                if r.returncode != 0:
                    raise PublishError(
                        f"git {' '.join(args)} failed: {r.stderr.strip()[:200]}",
                        code="git-failed",
                    )
                return r.stdout

            _git("checkout", "-B", branch)
            _git("add", "recipe/meta.yaml")
            _git(
                "-c", "user.email=release-kit@simtabi.com",
                "-c", "user.name=release-kit",
                "commit", "-m", f"bump to {self._version}",
            )

            # 4. Push to the fork. We need the token in the URL since
            # this is a non-interactive flow.
            from ...core.secrets import resolve_token
            resolution = resolve_token("github", env_var=self._env_var)
            if not resolution.resolved:
                raise PublishError(
                    f"no GitHub token resolved (env_var={self._env_var}). "
                    "Cannot push to the fork.",
                    code="token-not-found",
                )
            authed_url = (
                f"https://x-access-token:{resolution.value}"
                f"@github.com/{self._fork}.git"
            )
            try:
                subprocess.run(
                    ["git", "push", "--force-with-lease", authed_url, branch],
                    capture_output=True, text=True, check=True, timeout=120,
                    cwd=repo_root,
                )
            except subprocess.CalledProcessError as e:
                raise PublishError(
                    f"git push to {self._fork} failed: {e.stderr.strip()[:200]}",
                    code="push-failed",
                ) from e

            # 5. Open the PR via the API. Idempotent: if a PR with the
            # same head branch already exists, return that one.
            fork_owner = self._fork.split("/", 1)[0]
            head = f"{fork_owner}:{branch}"
            existing: object
            try:
                existing = self._api_get(
                    ctx,
                    f"/repos/{self._feedstock}/pulls?state=open&head={head}",
                    env_var=self._env_var,
                )
            except Exception:
                existing = []
            if isinstance(existing, list) and existing:
                first: object = existing[0]
                if isinstance(first, dict):
                    url = str(first.get("html_url", ""))
                    return StepOutcome(
                        step="publish",
                        status="ok",
                        detail=f"existing PR found: {url}",
                    )

            body: dict[str, object] = {
                "title": f"bump to {self._version}",
                "head": head,
                "base": "main",
                "body": (
                    f"Automated bump by release-kit.\n\n"
                    f"- version: `{self._version}`\n"
                    f"- sha256:  `{self._sha256}`\n"
                ),
            }
            try:
                pr = self._api_post(
                    ctx,
                    f"/repos/{self._feedstock}/pulls",
                    body,
                    env_var=self._env_var,
                )
            except Exception as e:
                raise PublishError(
                    f"PR creation against {self._feedstock} failed: {e}",
                    code="pr-create-failed",
                ) from e

        pr_url = str(pr.get("html_url", "")) if isinstance(pr, dict) else ""
        return StepOutcome(
            step="publish",
            status="ok",
            detail=f"PR opened: {pr_url}",
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
