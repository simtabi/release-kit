"""CLI smoke tests for the bootstrap-repo + rotate-tokens verbs.

The publish / doctor / init / version verbs are exercised by the
core/platforms tests already. These tests cover the wiring that's
unique to the two new commands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from release_kit.cli.app import app

runner = CliRunner()


def _write_config(tmp_path: Path, targets: dict) -> Path:
    cfg = {
        "project": {"name": "x", "version_source": "pyproject.toml"},
        "targets": targets,
    }
    p = tmp_path / "release.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def test_rotate_tokens_list_prints_table() -> None:
    res = runner.invoke(app, ["rotate-tokens", "--list"])
    assert res.exit_code == 0
    assert "PyPI" in res.stdout
    assert "pypi.org" in res.stdout


def test_rotate_tokens_unknown_platform_exits_2() -> None:
    res = runner.invoke(
        app, ["rotate-tokens", "--platform", "does-not-exist"], input="\n"
    )
    assert res.exit_code == 2


def test_rotate_tokens_blank_input_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blank token input skips the platform without writing to keyring."""
    called: dict = {}

    def fake_apply(slug: str, value: str) -> None:
        called["slug"] = slug

    monkeypatch.setattr(
        "release_kit.workflows.rotate_tokens.apply_rotation", fake_apply
    )
    res = runner.invoke(app, ["rotate-tokens", "--platform", "pypi"], input="\n")
    assert res.exit_code == 0
    assert "skipped" in res.stdout
    assert "slug" not in called


def test_bootstrap_repo_dry_run_no_targets(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, {})
    res = runner.invoke(app, ["bootstrap-repo", "--config", str(cfg)])
    assert res.exit_code == 0


def test_bootstrap_repo_dry_run_github(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    cfg = _write_config(
        tmp_path,
        {
            "github": {
                "enabled": True,
                "auth": "token",
                "repo": "o/r",
                "tag": "v1.0.0",
                "topics": ["oss"],
            }
        },
    )
    res = runner.invoke(app, ["bootstrap-repo", "--config", str(cfg)])
    assert res.exit_code == 0
    assert "github" in res.stdout
