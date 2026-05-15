"""Tests for npm-github + npm-gitlab."""

from __future__ import annotations

import pytest

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.npm_github import NpmGitHubPackages
from release_kit.platforms.registries.npm_gitlab import NpmGitLabRegistry


def _ctx() -> RunContext:
    return RunContext(dry_run=True, policies=PolicyConfig(), target_name="x")


def _build(cls, **extras):
    target = TargetConfig.model_validate({"enabled": True, "auth": "token", **extras})
    plat = cls.from_target(target)
    plat.__post_init__()
    return plat


# --- npm-github ----------------------------------------------------------


def test_npm_github_missing_scope(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(NpmGitHubPackages).authenticate(_ctx())
    assert exc.value.code == "missing-scope"


def test_npm_github_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(NpmGitHubPackages, scope="@simtabi").authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_npm_github_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    out = _build(NpmGitHubPackages, scope="@simtabi").authenticate(_ctx())
    assert out.status == "ok"


def test_npm_github_npmrc_lines(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    plat = _build(NpmGitHubPackages, scope="@simtabi")
    plat.authenticate(_ctx())
    lines = plat._npmrc_lines(_ctx())
    assert any("npm.pkg.github.com" in line for line in lines)
    assert any("@simtabi:registry" in line for line in lines)


# --- npm-gitlab ----------------------------------------------------------


def test_npm_gitlab_missing_project_id(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(NpmGitLabRegistry, scope="@simtabi").authenticate(_ctx())
    assert exc.value.code == "missing-project-id"


def test_npm_gitlab_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_NPM_TOKEN", "glpat_x")
    out = _build(NpmGitLabRegistry, scope="@g", project_id=42).authenticate(_ctx())
    assert out.status == "ok"


def test_npm_gitlab_npmrc_has_project_id(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_NPM_TOKEN", "glpat_x")
    plat = _build(NpmGitLabRegistry, scope="@g", project_id=42)
    plat.authenticate(_ctx())
    lines = plat._npmrc_lines(_ctx())
    assert any("projects/42" in line for line in lines)
