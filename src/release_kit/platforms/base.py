"""Platform abstractions.

A *platform* is anything release-kit can interact with: a package
registry, a git host, a sigstore service. The base class defines a
small surface every plugin implements:

- ``authenticate(ctx)`` — resolve credentials, fail fast if missing
- ``validate(ctx)``     — preflight (won't touch the network)
- ``publish(ctx)``      — the actual upload / API call
- ``verify(ctx)``       — post-publish HTTP HEAD / API read
- ``rollback(ctx)``     — best-effort cleanup; optional per platform

Each platform declares its :class:`AutomationLevel` and supported
:class:`AuthMethod` set as **class attributes** so the runner +
``doctor`` command can reason about readiness without instantiating
the platform.

Plugin discovery uses ``importlib.metadata.entry_points``:

    [project.entry-points."release_kit.platforms"]
    my-platform = "my_pkg.module:MyPlatform"

The bundled :func:`load_platform_classes` walks that entry-point
group and returns the registered classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from importlib.metadata import entry_points
from typing import ClassVar, Self

from ..core.config import TargetConfig
from ..core.errors import PlatformError
from ..core.runner import RunContext, StepOutcome


class AutomationLevel(StrEnum):
    """
    How automated a platform's publish flow can be end-to-end.

    See ``docs/playbook/cross-cutting/oidc-matrix.md`` for the
    matrix of which providers offer which level today.

    @member OIDC_API      Passwordless via CI OIDC + full API.
    @member FULL_API      Long-lived token + full HTTP/CLI automation.
    @member CLI_LOGIN     One-time interactive ``<tool> login``; rest auto.
    @member PR_BASED      Automation opens a PR; merge is human-gated.
    @member MANUAL_ONLY   No machine path; web UI required.
    """

    OIDC_API = "oidc_api"
    FULL_API = "full_api"
    CLI_LOGIN = "cli_login"
    PR_BASED = "pr_based"
    MANUAL_ONLY = "manual_only"


class AuthMethod(StrEnum):
    """
    Auth methods a platform can accept.

    @member OIDC       OpenID Connect trusted publisher.
    @member TOKEN      Long-lived API token / PAT / access token.
    @member BASIC      HTTP Basic (username + password / app password).
    @member CLI        ``<tool> login`` flow (AWS, gcloud, az).
    @member NONE       No auth (public read).
    """

    OIDC = "oidc"
    TOKEN = "token"
    BASIC = "basic"
    CLI = "cli"
    NONE = "none"


# ---------------------------------------------------------------------------
# Bases
# ---------------------------------------------------------------------------


@dataclass
class Platform(ABC):
    """
    Abstract base for any release-kit plugin.

    Subclasses declare these class attributes:

    - ``slug``                 stable string ID (matches config target key)
    - ``automation_level``     :class:`AutomationLevel`
    - ``supported_auth_methods``  tuple of :class:`AuthMethod`

    And implement the five lifecycle methods below.

    Instance state holds the resolved :class:`TargetConfig` block.

    @field  target  the config block for this platform's target key.
    """

    target: TargetConfig

    slug: ClassVar[str] = "abstract"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.MANUAL_ONLY
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = ()

    # ---- lifecycle ---------------------------------------------------

    @abstractmethod
    def authenticate(self, ctx: RunContext) -> StepOutcome:
        """
        Resolve credentials needed to publish.

        Implementations should NOT make network calls here; just
        confirm the token / OIDC config / CLI session is set up
        enough to call :py:meth:`publish` later. Network probes go
        in :py:meth:`verify`.

        @param  ctx  current run context.
        @return StepOutcome  step="authenticate"
        """

    @abstractmethod
    def validate(self, ctx: RunContext) -> StepOutcome:
        """
        Preflight: artifact present, version sane, policies honoured.

        Pure local checks; no network.

        @param  ctx
        @return StepOutcome  step="validate"
        """

    @abstractmethod
    def publish(self, ctx: RunContext) -> StepOutcome:
        """
        Execute the publish step.

        Honour ``ctx.dry_run`` strictly: no external mutation when
        ``ctx.dry_run=True``. Return ``StepOutcome.status="dry-run"``
        on the planned action.

        @param  ctx
        @return StepOutcome  step="publish"
        """

    def verify(self, ctx: RunContext) -> StepOutcome:
        """
        Post-publish: confirm the artifact is live + installable.

        Default implementation returns ``status="skipped"`` so
        platforms without a verification API can opt out cheaply.

        @param  ctx
        @return StepOutcome  step="verify"
        """
        return StepOutcome(step="verify", status="skipped", detail="no verify implemented")

    def rollback(self, ctx: RunContext) -> StepOutcome:
        """
        Best-effort cleanup after a failed publish.

        Most registries don't allow true delete; "rollback" usually
        means "yank" or "unlist". Default returns ``skipped``.

        @param  ctx
        @return StepOutcome  step="rollback"
        """
        return StepOutcome(step="rollback", status="skipped", detail="no rollback implemented")

    # ---- factory -----------------------------------------------------

    @classmethod
    def from_target(cls, target: TargetConfig) -> Self:
        """
        Construct a platform instance from its config block.

        Default returns ``cls(target=target)``; override for platforms
        that need richer initialisation.
        """
        return cls(target=target)


class Registry(Platform):
    """
    Marker subclass for package registries.

    Currently identical to :class:`Platform`; reserved for any
    registry-specific helpers we add later (e.g., artifact-listing).
    """


class GitHost(Platform):
    """
    Marker subclass for git hosts.

    Future helpers (branch protection, topics, releases) live here.
    """


# ---------------------------------------------------------------------------
# Entry-point plugin discovery
# ---------------------------------------------------------------------------


ENTRYPOINT_GROUP = "release_kit.platforms"


def load_platform_classes() -> dict[str, type[Platform]]:
    """
    Walk the ``release_kit.platforms`` entry-point group and return
    a dict of ``slug -> class``.

    Third parties register custom platforms by adding their own
    package entry-point under the same group; this function does
    not distinguish between bundled and third-party.

    @return dict[str, type[Platform]]
    @throws PlatformError  if a registered entry-point fails to
                           import or doesn't subclass Platform.
    """
    out: dict[str, type[Platform]] = {}
    for ep in entry_points(group=ENTRYPOINT_GROUP):
        try:
            cls = ep.load()
        except Exception as e:
            raise PlatformError(
                f"failed to load platform plugin {ep.name!r}: {e}",
                code="plugin-load-failed",
                remediation=f"Check that {ep.value} imports cleanly.",
            ) from e
        if not isinstance(cls, type) or not issubclass(cls, Platform):
            raise PlatformError(
                f"plugin {ep.name!r} is not a Platform subclass",
                code="plugin-not-platform",
            )
        # Honour the class's declared slug over the entry-point name when
        # they disagree; entry-point names should match by convention but
        # the class is canonical.
        out[cls.slug] = cls
    return out
