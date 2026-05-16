"""Tests for the conda-forge feedstock plugin."""

from __future__ import annotations

import pytest

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError, PublishError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.conda_forge import CondaForge


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="conda-forge")


def _plat(**extras) -> CondaForge:
    target = TargetConfig.model_validate({"enabled": True, "auth": "token", **extras})
    plat = CondaForge.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_invalid_feedstock(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(feedstock="just-name").authenticate(_ctx())
    assert exc.value.code == "invalid-feedstock"


def test_authenticate_invalid_fork(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(feedstock="conda-forge/x").authenticate(_ctx())
    assert exc.value.code == "invalid-fork"


def test_authenticate_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(
            feedstock="conda-forge/x", fork="user/x"
        ).authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAP_GITHUB_TOKEN", "ghp_x")
    out = _plat(feedstock="conda-forge/x", fork="user/x").authenticate(_ctx())
    assert out.status == "ok"


def test_validate_missing_version(monkeypatch: pytest.MonkeyPatch) -> None:
    plat = _plat(feedstock="conda-forge/x", fork="user/x")
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "missing-version"


def test_validate_invalid_sha256() -> None:
    plat = _plat(
        feedstock="conda-forge/x", fork="user/x", version="0.1.0", sha256="short"
    )
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "invalid-sha256"


def test_validate_ok() -> None:
    plat = _plat(
        feedstock="conda-forge/x",
        fork="user/x",
        version="0.1.0",
        sha256="a" * 64,
    )
    out = plat.validate(_ctx())
    assert out.status == "ok"
    assert "0.1.0" in out.detail


def test_publish_dry_run() -> None:
    plat = _plat(
        feedstock="conda-forge/x",
        fork="user/x",
        version="0.1.0",
        sha256="a" * 64,
    )
    out = plat.publish(_ctx(dry_run=True))
    assert out.status == "dry-run"
    assert "0.1.0" in out.detail


def test_publish_apply_raises_not_implemented() -> None:
    """The apply path explicitly raises so users don't get a half-done PR."""
    plat = _plat(
        feedstock="conda-forge/x",
        fork="user/x",
        version="0.1.0",
        sha256="a" * 64,
    )
    with pytest.raises(PublishError) as exc:
        plat.publish(_ctx(dry_run=False))
    assert exc.value.code == "not-implemented"
