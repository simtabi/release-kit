"""Tests for the pydantic config models + JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from release_kit.core.config import Config, PolicyConfig, ProjectConfig, TargetConfig
from release_kit.core.errors import ConfigError


def test_example_round_trips() -> None:
    """The bundled example dict must validate against Config."""
    cfg = Config.model_validate(Config.example())
    assert cfg.project.name == "my-project"
    assert "pypi" in cfg.targets
    assert cfg.targets["pypi"].enabled is True
    assert cfg.policies.default_dry_run is True


def test_from_path_loads_a_real_file(tmp_path: Path) -> None:
    p = tmp_path / "release.json"
    p.write_text(json.dumps(Config.example()), encoding="utf-8")
    cfg = Config.from_path(p)
    assert cfg.project.name == "my-project"


def test_from_path_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config file not found"):
        Config.from_path(tmp_path / "nope.json")


def test_from_path_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid JSON"):
        Config.from_path(p)


def test_from_path_schema_violation_raises(tmp_path: Path) -> None:
    """Empty project dict violates the schema (project.name required)."""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"project": {}}), encoding="utf-8")
    with pytest.raises(ConfigError, match="schema violation"):
        Config.from_path(p)


def test_targets_extra_keys_pass_through() -> None:
    """Target config uses extra='allow' so per-platform keys round-trip."""
    cfg = Config.model_validate(
        {
            "project": {"name": "x"},
            "targets": {
                "ghcr": {
                    "enabled": True,
                    "auth": "oidc",
                    "image": "ghcr.io/me/x",
                    "tags": ["latest", "v1"],
                }
            },
        }
    )
    extras = cfg.targets["ghcr"].model_extra or {}
    assert extras["image"] == "ghcr.io/me/x"
    assert extras["tags"] == ["latest", "v1"]


def test_target_auth_invalid_value_raises() -> None:
    """An auth string outside the literal set is rejected by pydantic."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Config.model_validate({"project": {"name": "x"}, "targets": {"pypi": {"auth": "fish"}}})


def test_policies_defaults() -> None:
    p = PolicyConfig()
    assert p.require_clean_git is True
    assert p.require_tag_match is True
    assert p.default_dry_run is True
    assert p.allow_token_auth is False


def test_enabled_targets_filters_disabled() -> None:
    cfg = Config.model_validate(
        {
            "project": {"name": "x"},
            "targets": {
                "a": {"enabled": True, "auth": "oidc"},
                "b": {"enabled": False, "auth": "token"},
            },
        }
    )
    enabled = cfg.enabled_targets()
    assert "a" in enabled
    assert "b" not in enabled


def test_project_version_source_validation() -> None:
    proj = ProjectConfig(name="x", version_source="pyproject.toml")
    assert proj.version_source == "pyproject.toml"
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProjectConfig(name="x", version_source="invalid-source")  # type: ignore[arg-type]


def test_target_name_must_be_trimmed() -> None:
    """Reject ``"  name"`` or ``"name  "`` because keys leak to filenames."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Config.model_validate(
            {"project": {"name": "x"}, "targets": {"  spaced": TargetConfig().model_dump()}}
        )


def test_bundled_schema_matches_model() -> None:
    """The shipped JSON schema must validate the example config."""
    from importlib import resources

    import jsonschema  # type: ignore[import-not-found]

    schema_text = (
        resources.files("release_kit") / "schema" / "release-kit.schema.json"
    ).read_text()
    schema = json.loads(schema_text)
    jsonschema.validate(instance=Config.example(), schema=schema)
