"""simtabi-release-kit — multi-registry publishing automation.

Public API:

    ReleaseKit          fluent entrypoint
    Config              JSON-config root model (pydantic)
    Platform            abstract base for any platform plugin
    Registry            subclass of Platform; package registries
    GitHost             subclass of Platform; git hosts
    AutomationLevel     enum: OIDC_API | FULL_API | CLI_LOGIN | PR_BASED | MANUAL_ONLY
    AuthMethod          enum: OIDC | TOKEN | BASIC | NONE

Layout::

    core/
        config.py       pydantic config models
        env.py          .env loader
        secrets.py      token resolution chain
        logging.py      structlog setup
        errors.py       typed exception hierarchy
        runner.py       dry-run + idempotency primitives
    platforms/
        base.py         Platform / Registry / GitHost ABCs
        registries/     one module per registry
        git_hosts/      one module per git host
    workflows/          composed multi-platform flows
    cli/                Typer entry points
    schema/             JSON Schema for the config

Read ``docs/architecture.md`` for the extension contract.
"""

from __future__ import annotations

from importlib import metadata as _md

from .core.config import (
    Config,
    PolicyConfig,
    ProjectConfig,
    ProvenanceConfig,
    TargetConfig,
)
from .core.errors import (
    AuthenticationError,
    ConfigError,
    PlatformError,
    PublishError,
    ReleaseKitError,
    ValidationError,
)
from .platforms.base import (
    AuthMethod,
    AutomationLevel,
    GitHost,
    Platform,
    Registry,
)

try:
    __version__ = _md.version("simtabi-release-kit")
except _md.PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "AuthMethod",
    "AuthenticationError",
    "AutomationLevel",
    "Config",
    "ConfigError",
    "GitHost",
    "Platform",
    "PlatformError",
    "PolicyConfig",
    "ProjectConfig",
    "ProvenanceConfig",
    "PublishError",
    "Registry",
    "ReleaseKitError",
    "TargetConfig",
    "ValidationError",
    "__version__",
]
