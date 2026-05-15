"""Tests for the PyPI reference platform."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError, ValidationError, VerifyError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.pypi import PyPI


def _make_pypi(**extras) -> PyPI:
    """Construct a PyPI plugin with the given target options."""
    target = TargetConfig.model_validate({"enabled": True, "auth": "oidc", **extras})
    plat = PyPI.from_target(target)
    plat.__post_init__()  # type: ignore[attr-defined]
    return plat


def _ctx(*, dry_run: bool = True, allow_token: bool = False) -> RunContext:
    return RunContext(
        dry_run=dry_run,
        policies=PolicyConfig(allow_token_auth=allow_token),
        target_name="pypi",
    )


# --- authenticate ----------------------------------------------------------


def test_authenticate_oidc_in_ci_returns_ok(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GitHub Actions env marker signals OIDC is available."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    plat = _make_pypi()
    out = plat.authenticate(_ctx())
    assert out.status == "ok"
    assert "OIDC" in out.detail


def test_authenticate_oidc_no_ci_no_fallback_raises(clean_env: None) -> None:
    """When OIDC unavailable + allow_token_auth=False, refuse to publish."""
    plat = _make_pypi()
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "oidc-not-available"


def test_authenticate_oidc_no_ci_falls_back_with_policy(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """allow_token_auth=True + token in env resolves cleanly."""
    monkeypatch.setenv("PYPI_TOKEN", "pypi-AgEItestxxx")
    plat = _make_pypi()
    out = plat.authenticate(_ctx(allow_token=True))
    assert out.status == "ok"
    assert "token resolved" in out.detail


def test_authenticate_token_path_missing_token_raises(clean_env: None) -> None:
    plat = _make_pypi(auth="token")
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "token-not-found"


# --- validate --------------------------------------------------------------


def test_validate_no_dist_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without any dist/*, validate raises ValidationError."""
    monkeypatch.chdir(tmp_path)
    plat = _make_pypi()
    with pytest.raises(ValidationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "no-dist"


def test_validate_dist_present_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "foo-0.1.0.tar.gz").write_bytes(b"")
    (tmp_path / "dist" / "foo-0.1.0-py3-none-any.whl").write_bytes(b"")
    plat = _make_pypi()
    out = plat.validate(_ctx())
    assert out.status == "ok"
    assert "2 dist file(s)" in out.detail


# --- publish (dry-run only; we never invoke real twine in unit tests) ------


def test_publish_dry_run_does_not_execute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "x-0.1.0.tar.gz").write_bytes(b"")
    plat = _make_pypi()
    out = plat.publish(_ctx(dry_run=True))
    assert out.status == "dry-run"
    assert "twine upload" in out.detail


# --- verify ----------------------------------------------------------------


@respx.mock
def test_verify_200_returns_ok() -> None:
    plat = _make_pypi(project_name="simtabi-release-kit")
    respx.get("https://pypi.org/pypi/simtabi-release-kit/json").mock(
        return_value=httpx.Response(200, json={"info": {"version": "0.1.0"}})
    )
    out = plat.verify(_ctx())
    assert out.status == "ok"
    assert "0.1.0" in out.detail


@respx.mock
def test_verify_404_raises() -> None:
    plat = _make_pypi(project_name="nope-does-not-exist-pypi")
    respx.get("https://pypi.org/pypi/nope-does-not-exist-pypi/json").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(VerifyError) as exc:
        plat.verify(_ctx())
    assert exc.value.code == "verify-not-found"


@respx.mock
def test_verify_5xx_raises() -> None:
    plat = _make_pypi(project_name="srv-error")
    respx.get("https://pypi.org/pypi/srv-error/json").mock(return_value=httpx.Response(503))
    with pytest.raises(VerifyError) as exc:
        plat.verify(_ctx())
    assert exc.value.code == "verify-bad-status"


def test_verify_no_project_name_skipped() -> None:
    """When project_name isn't in config, verify returns skipped, not error."""
    plat = _make_pypi()  # no project_name
    out = plat.verify(_ctx())
    assert out.status == "skipped"


@respx.mock
def test_verify_testpypi_uses_test_endpoint() -> None:
    plat = _make_pypi(repository="testpypi", project_name="pkg")
    respx.get("https://test.pypi.org/pypi/pkg/json").mock(
        return_value=httpx.Response(200, json={"info": {"version": "1.0.0"}})
    )
    out = plat.verify(_ctx())
    assert out.status == "ok"
