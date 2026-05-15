"""Tests for the Platform abstractions + entry-point discovery."""

from __future__ import annotations

from release_kit.platforms.base import (
    AuthMethod,
    AutomationLevel,
    GitHost,
    Registry,
    load_platform_classes,
)


def test_automation_level_enum_values() -> None:
    """All five automation levels are present and stringly-equal."""
    assert AutomationLevel.OIDC_API.value == "oidc_api"
    assert AutomationLevel.FULL_API.value == "full_api"
    assert AutomationLevel.CLI_LOGIN.value == "cli_login"
    assert AutomationLevel.PR_BASED.value == "pr_based"
    assert AutomationLevel.MANUAL_ONLY.value == "manual_only"


def test_auth_method_enum_values() -> None:
    assert AuthMethod.OIDC.value == "oidc"
    assert AuthMethod.TOKEN.value == "token"
    assert AuthMethod.BASIC.value == "basic"
    assert AuthMethod.CLI.value == "cli"
    assert AuthMethod.NONE.value == "none"


def test_registry_is_platform_subclass() -> None:
    """The marker subclasses are themselves classes, not just type aliases."""
    from release_kit.platforms.base import Platform
    assert issubclass(Registry, Platform)
    assert issubclass(GitHost, Platform)


def test_load_platform_classes_finds_pypi() -> None:
    """The PyPI entry-point declared in pyproject.toml must resolve."""
    classes = load_platform_classes()
    assert "pypi" in classes
    from release_kit.platforms.registries.pypi import PyPI
    assert classes["pypi"] is PyPI


def test_pypi_class_attributes() -> None:
    """PyPI declares the expected level + auth methods."""
    from release_kit.platforms.registries.pypi import PyPI
    assert PyPI.slug == "pypi"
    assert PyPI.automation_level == AutomationLevel.OIDC_API
    assert AuthMethod.OIDC in PyPI.supported_auth_methods
    assert AuthMethod.TOKEN in PyPI.supported_auth_methods
