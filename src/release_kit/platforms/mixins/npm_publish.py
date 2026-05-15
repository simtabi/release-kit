"""npm publish mixin.

Shared by every npm-protocol registry: npmjs.org, GitHub Packages npm,
GitLab npm. Each subclass overrides the registry URL + auth setup
(.npmrc generation); everything else is shared.
"""

from __future__ import annotations

import contextlib
from abc import abstractmethod
from pathlib import Path

from ...core.errors import PublishError
from ...core.runner import RunContext, StepOutcome, run_command


class NpmPublishMixin:
    """
    Shared npm publish flow.

    Subclasses must implement:

    - ``_npmrc_lines(ctx)``  returns the lines to write into an ad-hoc .npmrc
    - ``_publish_args(ctx)`` returns extra args for ``npm publish``
                             (``["--access", "public"]``, ``["--provenance"]``).

    The mixin's :py:meth:`_do_publish`:

    1. Writes a transient ``.npmrc`` in the package dir.
    2. Runs ``npm publish <args>``.
    3. Removes the ``.npmrc`` whether publish succeeded or failed.

    Honours ``ctx.dry_run`` strictly.
    """

    # ---- abstract surface ------------------------------------------------

    @abstractmethod
    def _npmrc_lines(self, ctx: RunContext) -> list[str]:
        """Lines to write into a temp .npmrc. Empty list = skip the write."""

    @abstractmethod
    def _publish_args(self, ctx: RunContext) -> list[str]:
        """Extra args for ``npm publish`` (after the subcommand)."""

    @property
    def _package_dir(self) -> Path:
        """Where ``package.json`` lives. Override per subclass if needed."""
        return Path()

    # ---- shared flow -----------------------------------------------------

    def _do_publish(self, ctx: RunContext) -> StepOutcome:
        """
        Run ``npm publish`` with a per-invocation .npmrc.

        @param  ctx
        @return StepOutcome  step="publish"
        """
        lines = self._npmrc_lines(ctx)
        extra_args = self._publish_args(ctx)
        argv = ["npm", "publish", *extra_args]

        if ctx.dry_run:
            return StepOutcome(
                step="publish",
                status="dry-run",
                detail=f"would run: {' '.join(argv)}",
            )

        npmrc = self._package_dir / ".npmrc"
        wrote_npmrc = False
        if lines:
            npmrc.write_text("\n".join(lines) + "\n", encoding="utf-8")
            npmrc.chmod(0o600)
            wrote_npmrc = True

        try:
            run_command(argv, dry_run=False, check=True, cwd=str(self._package_dir))
        except Exception as e:
            raise PublishError(
                f"npm publish failed: {e}",
                code="npm-publish-failed",
            ) from e
        finally:
            if wrote_npmrc and npmrc.exists():
                with contextlib.suppress(OSError):
                    npmrc.unlink()
        return StepOutcome(step="publish", status="ok", detail="published via npm")
