"""Tests for the standalone registries: rubygems, cargo, nuget, packagist, maven-central."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.cargo import CratesIo
from release_kit.platforms.registries.maven_central import MavenCentral
from release_kit.platforms.registries.nuget import NuGet
from release_kit.platforms.registries.packagist import Packagist
from release_kit.platforms.registries.rubygems import RubyGems


def _ctx() -> RunContext:
    return RunContext(dry_run=True, policies=PolicyConfig(), target_name="x")


def _build(cls, **extras):
    auth = extras.pop("_auth", "token")
    target = TargetConfig.model_validate({"enabled": True, "auth": auth, **extras})
    plat = cls.from_target(target)
    plat.__post_init__()
    return plat


# --- rubygems ------------------------------------------------------------


def test_rubygems_missing_gemspec(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(RubyGems).authenticate(_ctx())
    assert exc.value.code == "missing-gemspec"


def test_rubygems_oidc_path_ok(clean_env: None) -> None:
    out = _build(RubyGems, _auth="oidc", gemspec="x.gemspec").authenticate(_ctx())
    assert out.status == "ok"


def test_rubygems_token_missing(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(RubyGems, gemspec="x.gemspec").authenticate(_ctx())
    assert exc.value.code == "token-not-found"


@respx.mock
def test_rubygems_verify_ok(clean_env: None) -> None:
    plat = _build(RubyGems, gemspec="x.gemspec", gem_name="release-kit")
    respx.get("https://rubygems.org/api/v1/gems/release-kit.json").mock(
        return_value=httpx.Response(200, json={"version": "1.0.0"})
    )
    out = plat.verify(_ctx())
    assert out.status == "ok"


# --- cargo ---------------------------------------------------------------


def test_cargo_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(CratesIo).authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_cargo_missing_manifest(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CARGO_REGISTRY_TOKEN", "x")
    plat = _build(CratesIo, manifest_path=str(tmp_path / "missing.toml"))
    plat.authenticate(_ctx())
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "no-manifest"


# --- nuget ---------------------------------------------------------------


def test_nuget_no_packages(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUGET_API_KEY", "k")
    plat = _build(NuGet)
    plat.authenticate(_ctx())
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "no-packages"


# --- packagist -----------------------------------------------------------


def test_packagist_invalid_package(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(Packagist, package="single").authenticate(_ctx())
    assert exc.value.code == "invalid-package"


def test_packagist_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PACKAGIST_TOKEN", "x")
    out = _build(
        Packagist, package="me/pkg", username="me",
    ).authenticate(_ctx())
    assert out.status == "ok"


@respx.mock
def test_packagist_verify_lists_versions(clean_env: None) -> None:
    plat = _build(
        Packagist, package="me/pkg", username="me", repository="https://github.com/me/pkg",
    )
    respx.get("https://packagist.org/packages/me/pkg.json").mock(
        return_value=httpx.Response(200, json={"package": {"versions": {"1.0.0": {}, "1.1.0": {}}}})
    )
    out = plat.verify(_ctx())
    assert "2 versions" in out.detail


# --- maven-central -------------------------------------------------------


def test_maven_central_missing_user_or_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(MavenCentral).authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_maven_central_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CENTRAL_TOKEN_USER", "u")
    monkeypatch.setenv("CENTRAL_TOKEN_VALUE", "v")
    out = _build(MavenCentral).authenticate(_ctx())
    assert out.status == "ok"


def test_maven_central_invalid_build_tool(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CENTRAL_TOKEN_USER", "u")
    monkeypatch.setenv("CENTRAL_TOKEN_VALUE", "v")
    plat = _build(MavenCentral, build_tool="rake")
    plat.authenticate(_ctx())
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "invalid-build-tool"
