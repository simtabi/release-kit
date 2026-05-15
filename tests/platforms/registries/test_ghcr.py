"""Tests for the GHCR platform."""

from __future__ import annotations

import pytest

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.ghcr import GHCR


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="ghcr")


def _plat(**extras) -> GHCR:
    target = TargetConfig.model_validate({"enabled": True, "auth": "oidc", **extras})
    plat = GHCR.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_missing_image(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat().authenticate(_ctx())
    assert exc.value.code == "missing-image"


def test_authenticate_image_must_start_with_ghcr(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(image="docker.io/me/x").authenticate(_ctx())
    assert exc.value.code == "invalid-image"


def test_authenticate_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(image="ghcr.io/me/x").authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    out = _plat(image="ghcr.io/me/x").authenticate(_ctx())
    assert out.status == "ok"


def test_publish_dry_run() -> None:
    out = _plat(image="ghcr.io/me/x", tags=["v1"]).publish(_ctx())
    assert out.status == "dry-run"
