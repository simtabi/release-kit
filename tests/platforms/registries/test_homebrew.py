"""Tests for the Homebrew tap publisher."""

from __future__ import annotations

import pytest

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.homebrew import Homebrew


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="homebrew")


def _plat(**extras) -> Homebrew:
    target = TargetConfig.model_validate({"enabled": True, "auth": "token", **extras})
    plat = Homebrew.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_invalid_tap(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(tap="just-name", formula="x").authenticate(_ctx())
    assert exc.value.code == "invalid-tap"


def test_authenticate_missing_formula(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(tap="o/r").authenticate(_ctx())
    assert exc.value.code == "missing-formula"


def test_authenticate_missing_token(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat(tap="o/r", formula="f").authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAP_GITHUB_TOKEN", "ghp_x")
    out = _plat(tap="o/r", formula="f").authenticate(_ctx())
    assert out.status == "ok"


def test_validate_missing_sdist_url(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TAP_GITHUB_TOKEN", "ghp_x")
    plat = _plat(tap="o/r", formula="f")
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "missing-sdist-url"


def test_publish_dry_run() -> None:
    plat = _plat(tap="o/r", formula="f", sdist_url="https://example.com/x.tar.gz")
    out = plat.publish(_ctx())
    assert out.status == "dry-run"
