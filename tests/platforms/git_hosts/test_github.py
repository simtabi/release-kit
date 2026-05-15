"""Tests for the GitHub.com host."""

from __future__ import annotations

import httpx
import pytest
import respx

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.git_hosts.github import GitHub


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="github")


def _plat(**extras) -> GitHub:
    target = TargetConfig.model_validate({"enabled": True, "auth": "oidc", **extras})
    plat = GitHub.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_bad_repo(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(repo="just-a-name").authenticate(_ctx())
    assert exc.value.code == "invalid-repo"


def test_authenticate_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(repo="owner/repo").authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    out = _plat(repo="owner/repo").authenticate(_ctx())
    assert out.status == "ok"


def test_validate_missing_tag(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    plat = _plat(repo="o/r")
    plat.authenticate(_ctx())
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "missing-tag"


def test_publish_dry_run() -> None:
    plat = _plat(repo="o/r", tag="v1.0.0")
    out = plat.publish(_ctx())
    assert out.status == "dry-run"
    assert "v1.0.0" in out.detail


@respx.mock
def test_publish_apply_calls_releases_endpoint(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    route = respx.post("https://api.github.com/repos/o/r/releases").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    plat = _plat(repo="o/r", tag="v1.0.0")
    out = plat.publish(_ctx(dry_run=False))
    assert route.called
    assert out.status == "ok"
