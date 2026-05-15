"""Tests for the GitLab.com host."""

from __future__ import annotations

import httpx
import pytest
import respx

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.git_hosts.gitlab import GitLab


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="gitlab")


def _plat(**extras) -> GitLab:
    target = TargetConfig.model_validate({"enabled": True, "auth": "oidc", **extras})
    plat = GitLab.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_missing_project(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat().authenticate(_ctx())
    assert exc.value.code == "missing-project"


def test_authenticate_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(project="group/project").authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_ok_with_numeric_id(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat_x")
    out = _plat(project_id=42).authenticate(_ctx())
    assert out.status == "ok"
    assert "42" in out.detail


def test_publish_dry_run() -> None:
    plat = _plat(project="g/p", tag="v1.0.0")
    out = plat.publish(_ctx())
    assert out.status == "dry-run"


@respx.mock
def test_publish_url_encodes_project_path(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat_x")
    route = respx.post("https://gitlab.com/api/v4/projects/g%2Fp/releases").mock(
        return_value=httpx.Response(201, json={"name": "v1"})
    )
    plat = _plat(project="g/p", tag="v1")
    plat.publish(_ctx(dry_run=False))
    assert route.called
