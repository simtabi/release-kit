"""Tests for the npm platform."""

from __future__ import annotations

from pathlib import Path

import pytest

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.npm import Npm


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="npm")


def _plat(**extras) -> Npm:
    target = TargetConfig.model_validate({"enabled": True, "auth": "oidc", **extras})
    plat = Npm.from_target(target)
    plat.__post_init__()
    return plat


def test_authenticate_no_token_no_provenance_raises(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _plat().authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_authenticate_provenance_path_passes_without_token(clean_env: None) -> None:
    out = _plat(provenance=True).authenticate(_ctx())
    assert out.status == "ok"


def test_validate_no_package_json(tmp_path: Path) -> None:
    plat = _plat(package_dir=str(tmp_path))
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "no-package-json"


def test_validate_ok(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"x","version":"1.0.0"}')
    plat = _plat(package_dir=str(tmp_path))
    out = plat.validate(_ctx())
    assert out.status == "ok"


def test_publish_dry_run(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NPM_TOKEN", "x")
    plat = _plat()
    plat.authenticate(_ctx())
    out = plat.publish(_ctx())
    assert out.status == "dry-run"
    assert "npm publish" in out.detail


def test_publish_args_include_access_and_provenance() -> None:
    plat = _plat(provenance=True, access="restricted")
    args = plat._publish_args(_ctx())
    assert "--access" in args
    assert "restricted" in args
    assert "--provenance" in args
