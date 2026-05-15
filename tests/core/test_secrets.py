"""Tests for the token resolution chain."""

from __future__ import annotations

import pytest

from release_kit.core.secrets import (
    TokenResolution,
    resolve_token,
)


def test_override_wins(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYPI_TOKEN", "from-env")
    r = resolve_token("pypi", env_var="PYPI_TOKEN", override="explicit")
    assert r.value == "explicit"
    assert r.source == "override"


def test_env_var_resolves(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYPI_TOKEN", "abc123def456")
    r = resolve_token("pypi", env_var="PYPI_TOKEN")
    assert r.value == "abc123def456"
    assert r.source == "env:PYPI_TOKEN"


def test_generic_fallback_env(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELEASE_KIT_TOKEN_PYPI", "fallback")
    r = resolve_token("pypi", env_var="PYPI_TOKEN")
    assert r.value == "fallback"
    assert r.source == "env:RELEASE_KIT_TOKEN_PYPI"


def test_generic_fallback_kebab_to_underscore(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A kebab-case key like ``"npm-github"`` maps to ``RELEASE_KIT_TOKEN_NPM_GITHUB``."""
    monkeypatch.setenv("RELEASE_KIT_TOKEN_NPM_GITHUB", "ghp_xxx")
    r = resolve_token("npm-github", env_var="NPM_GITHUB_TOKEN")
    assert r.value == "ghp_xxx"


def test_no_resolution_returns_unresolved(clean_env: None) -> None:
    r = resolve_token("pypi", env_var="PYPI_TOKEN")
    assert r.value is None
    assert r.resolved is False
    assert r.source == "none"


def test_preview_redacts_value(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Preview never contains the full token."""
    monkeypatch.setenv("PYPI_TOKEN", "pypi-AgEIabcdef1234567890")
    r = resolve_token("pypi", env_var="PYPI_TOKEN")
    assert "abcdef" not in r.preview
    assert "***" in r.preview
    assert r.preview.startswith("pypi")


def test_resolution_is_frozen() -> None:
    """TokenResolution dataclass is immutable (frozen=True)."""
    from dataclasses import FrozenInstanceError

    r = TokenResolution(value="x", source="env:X", preview="x***")
    with pytest.raises(FrozenInstanceError):
        r.value = "y"  # type: ignore[misc]
