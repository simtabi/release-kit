"""Pydantic v2 config models.

The single ``Config`` class is the root; everything else is a
sub-model. JSON Schema generation is exposed via
:py:meth:`Config.model_json_schema`. The bundled schema at
``release_kit/schema/release-kit.schema.json`` is the
machine-readable copy that ships with the wheel; regenerate via
``release-kit config dump-schema``.

Three layers of precedence at load time (handled by the CLI):

1. CLI flags
2. Environment variables (loaded from `.env` in dev)
3. JSON config

This module knows only about layer 3. The override layers compose
with :py:meth:`Config.model_copy(update=...)`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import ConfigError

# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


VersionSource = Literal[
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "pom.xml",
    "git-tag",
]


class ProjectConfig(BaseModel):
    """Identity + version source for the project being released."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    version_source: VersionSource = "pyproject.toml"
    version_file: str | None = Field(
        default=None,
        description=(
            "Custom path when ``version_source`` is a non-standard file "
            "(e.g., ``VERSION``). Ignored otherwise."
        ),
    )


class TargetConfig(BaseModel):
    """
    Per-target configuration.

    ``enabled`` gates whether the target participates in ``publish``.
    ``auth`` declares the preferred auth method: ``oidc``, ``token``,
    or ``cli`` (for CLI-login flows like AWS/GCP/Azure). Extra
    per-target keys (registry URL, image name, draft flag, ...)
    are passed through as a free-form ``options`` dict so new
    platforms don't require schema migrations.
    """

    model_config = ConfigDict(extra="allow")  # platforms add their own keys

    enabled: bool = True
    auth: Literal["oidc", "token", "cli", "none"] = "oidc"


class PolicyConfig(BaseModel):
    """Global publish-time policies enforced by the runner."""

    model_config = ConfigDict(extra="forbid")

    require_clean_git: bool = True
    """Refuse to publish from a dirty working tree."""

    require_tag_match: bool = True
    """Tag name must equal ``v`` + the version_source's version."""

    require_signed_tag: bool = False
    """Refuse unsigned tags (gpg / ssh signed)."""

    require_changelog: bool = True
    """Require a dated section in CHANGELOG.md for this version."""

    continue_on_error: bool = False
    """When True, a failing target doesn't abort other targets."""

    default_dry_run: bool = True
    """When True, ``publish`` runs dry-run unless ``--apply`` is set."""

    allow_token_auth: bool = False
    """When False (default), refuse to fall back from OIDC to a token without --allow-token-auth."""

    parallel_publish: bool = False
    """When True, publish targets concurrently in a thread pool (default: serial)."""

    max_workers: int = Field(default=4, ge=1, le=32)
    """Worker count when parallel_publish is True (1..32; default: 4)."""


class Config(BaseModel):
    """
    Root config model.

    Pass either a path to a JSON file (``Config.from_path``) or a
    parsed dict (``Config.model_validate``). The CLI uses
    ``from_path`` and then layers env vars + flags on top via
    :py:meth:`merged`.

    @see  docs/configuration.md  for the full schema reference.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: str | None = Field(default=None, alias="$schema")
    project: ProjectConfig
    targets: dict[str, TargetConfig] = Field(default_factory=dict)
    policies: PolicyConfig = Field(default_factory=PolicyConfig)

    @field_validator("targets")
    @classmethod
    def _target_names(cls, v: dict[str, TargetConfig]) -> dict[str, TargetConfig]:
        """Reject empty / whitespace target names early."""
        for name in v:
            if not name.strip() or name != name.strip():
                raise ValueError(f"target name must be non-empty + trimmed: {name!r}")
        return v

    # ---- IO ----------------------------------------------------------

    @classmethod
    def from_path(cls, path: str | Path) -> Config:
        """
        Load + validate a JSON config file.

        @param  path  filesystem path to ``release.json`` (or alike).
        @return Config
        @throws ConfigError  on missing file, invalid JSON, or schema
                             violation.
        """
        p = Path(path).expanduser()
        if not p.is_file():
            raise ConfigError(
                f"config file not found: {p}",
                code="config-not-found",
                remediation=f"Run `release-kit init` to scaffold one at {p}.",
            )
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"invalid JSON in {p}: {e}",
                code="config-invalid-json",
                remediation="Run a JSON formatter (jq, prettier) on the file.",
            ) from e
        try:
            return cls.model_validate(data)
        except Exception as e:  # pydantic.ValidationError is too broad to import
            raise ConfigError(
                f"config schema violation: {e}",
                code="config-invalid",
                remediation="Validate against src/release_kit/schema/release-kit.schema.json.",
            ) from e

    def enabled_targets(self) -> dict[str, TargetConfig]:
        """Return the subset of targets with ``enabled=True``."""
        return {name: t for name, t in self.targets.items() if t.enabled}

    @classmethod
    def example(cls) -> dict[str, Any]:
        """A complete example config dict, used by ``release-kit init``."""
        return {
            "$schema": "./schema/release-kit.schema.json",
            "project": {
                "name": "my-project",
                "version_source": "pyproject.toml",
            },
            "targets": {
                "pypi": {"enabled": True, "auth": "oidc"},
            },
            "policies": {
                "require_clean_git": True,
                "require_tag_match": True,
                "continue_on_error": False,
                "default_dry_run": True,
            },
        }
