"""Tests for the Docker Hub platform."""

from __future__ import annotations

import httpx
import pytest
import respx

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError, VerifyError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.dockerhub import DockerHub


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="dockerhub")


def _plat(**extras) -> DockerHub:
    target = TargetConfig.model_validate({"enabled": True, "auth": "token", **extras})
    plat = DockerHub.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_missing_username_via_authenticate(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(image="me/img").authenticate(_ctx())
    assert exc.value.code == "missing-username"


def test_authenticate_missing_token_raises(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    plat = _plat(username="user", image="me/img")
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_ok_when_token_present(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOCKERHUB_TOKEN", "dckr_pat_x")
    plat = _plat(username="user", image="me/img")
    out = plat.authenticate(_ctx())
    assert out.status == "ok"
    assert "username=user" in out.detail


def test_validate_missing_image_raises() -> None:
    plat = _plat(username="user")
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "missing-image"


def test_publish_dry_run() -> None:
    plat = _plat(username="user", image="me/img", tags=["v1", "latest"])
    out = plat.publish(_ctx(dry_run=True))
    assert out.status == "dry-run"
    assert "2 tag(s)" in out.detail


@respx.mock
def test_verify_200_ok() -> None:
    plat = _plat(username="user", image="me/img", tags=["1.0.0"])
    respx.get("https://hub.docker.com/v2/repositories/me/img/tags/1.0.0/").mock(
        return_value=httpx.Response(200, json={"name": "1.0.0"})
    )
    out = plat.verify(_ctx())
    assert out.status == "ok"


@respx.mock
def test_verify_404_raises() -> None:
    plat = _plat(username="user", image="me/img", tags=["nope"])
    respx.get("https://hub.docker.com/v2/repositories/me/img/tags/nope/").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(VerifyError) as exc:
        plat.verify(_ctx())
    assert exc.value.code == "verify-not-found"


def test_verify_no_image_skipped() -> None:
    plat = _plat(username="user")
    out = plat.verify(_ctx())
    assert out.status == "skipped"
