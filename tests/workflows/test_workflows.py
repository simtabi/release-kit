"""Tests for the three workflow composition modules.

publish:         multi-target lifecycle composition + continue_on_error.
bootstrap_repo:  topics application + per-host gating.
rotate_tokens:   rotation table coverage + keyring write.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from release_kit.core.config import (
    Config,
    PolicyConfig,
    ProjectConfig,
    TargetConfig,
)
from release_kit.workflows.bootstrap_repo import run_bootstrap
from release_kit.workflows.publish import run_publish
from release_kit.workflows.rotate_tokens import (
    ROTATION_TABLE,
    apply_rotation,
    get_rotation_step,
)

# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


def _make_config(**targets) -> Config:
    return Config(
        project=ProjectConfig(name="x"),
        targets={k: TargetConfig.model_validate(v) for k, v in targets.items()},
        policies=PolicyConfig(continue_on_error=False),
    )


def test_publish_dry_run_pypi_only(clean_env: None) -> None:
    """pypi with no dist files should fail validate, but report should capture it."""
    cfg = _make_config(pypi={"enabled": True, "auth": "oidc", "package": "x"})
    report = run_publish(cfg, apply=False)
    assert "pypi" in report.target_outcomes
    # validate fails because there's no dist/ on disk.
    steps = [s.step for s in report.target_outcomes["pypi"]]
    assert "authenticate" in steps


def test_publish_unknown_target_emits_failure(clean_env: None) -> None:
    cfg = _make_config(does_not_exist={"enabled": True, "auth": "token"})
    report = run_publish(cfg, apply=False)
    assert len(report.failures) >= 1
    assert any("no plugin registered" in f.detail for f in report.failures)


def test_publish_disabled_target_is_skipped(clean_env: None) -> None:
    cfg = _make_config(pypi={"enabled": False, "auth": "oidc", "package": "x"})
    report = run_publish(cfg, selected=["pypi"], apply=False)
    # Disabled targets fall through and produce no outcomes entry.
    assert "pypi" not in report.target_outcomes


def test_publish_continue_on_error_proceeds_to_next(clean_env: None) -> None:
    cfg = Config(
        project=ProjectConfig(name="x"),
        targets={
            "missing": TargetConfig.model_validate({"enabled": True, "auth": "token"}),
            "pypi": TargetConfig.model_validate({"enabled": True, "auth": "oidc", "package": "x"}),
        },
        policies=PolicyConfig(continue_on_error=True),
    )
    report = run_publish(cfg, apply=False)
    # Both targets should appear in the report.
    assert "missing" in report.target_outcomes
    assert "pypi" in report.target_outcomes


# ---------------------------------------------------------------------------
# bootstrap_repo
# ---------------------------------------------------------------------------


def test_bootstrap_dry_run_github_topics(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    cfg = _make_config(
        github={
            "enabled": True,
            "auth": "token",
            "repo": "owner/repo",
            "tag": "v1.0.0",
            "topics": ["oss", "python"],
        }
    )
    report = run_bootstrap(cfg, apply=False)
    steps = report.target_outcomes["github"]
    statuses = [s.status for s in steps]
    assert "dry-run" in statuses
    assert any("would set 2 topic(s)" in s.detail for s in steps)


@respx.mock
def test_bootstrap_apply_calls_topics_endpoint(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    route = respx.put("https://api.github.com/repos/o/r/topics").mock(
        return_value=httpx.Response(200, json={"names": ["oss"]})
    )
    cfg = _make_config(
        github={
            "enabled": True,
            "auth": "token",
            "repo": "o/r",
            "tag": "v1.0.0",
            "topics": ["oss"],
        }
    )
    report = run_bootstrap(cfg, apply=True)
    steps = report.target_outcomes["github"]
    assert any(s.status == "ok" and "applied 1 topic" in s.detail for s in steps)
    assert route.called


def test_bootstrap_dry_run_branch_protection(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    cfg = _make_config(
        github={
            "enabled": True,
            "auth": "token",
            "repo": "o/r",
            "tag": "v1.0.0",
            "branch_protection": {
                "branch": "main",
                "enforce_admins": True,
                "required_pull_request_reviews": {
                    "required_approving_review_count": 1
                },
            },
        }
    )
    report = run_bootstrap(cfg, apply=False)
    steps = report.target_outcomes["github"]
    bp = [s for s in steps if s.step == "branch_protection"]
    assert bp
    assert bp[0].status == "dry-run"
    assert "PUT /repos/o/r/branches/main/protection" in bp[0].detail


@respx.mock
def test_bootstrap_apply_calls_branch_protection_endpoint(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    route = respx.put(
        "https://api.github.com/repos/o/r/branches/main/protection"
    ).mock(return_value=httpx.Response(200, json={"url": "..."}))
    cfg = _make_config(
        github={
            "enabled": True,
            "auth": "token",
            "repo": "o/r",
            "tag": "v1.0.0",
            "branch_protection": {
                "branch": "main",
                "enforce_admins": True,
            },
        }
    )
    report = run_bootstrap(cfg, apply=True)
    steps = report.target_outcomes["github"]
    bp = [s for s in steps if s.step == "branch_protection"]
    assert bp
    assert bp[0].status == "ok"
    assert "applied to main" in bp[0].detail
    assert route.called
    # Ensure the `branch` key was stripped from the body (it's part of
    # the URL, not the payload).
    body = json.loads(route.calls.last.request.content)
    assert "branch" not in body
    assert body.get("enforce_admins") is True


def test_bootstrap_no_branch_protection_emits_no_step(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without `branch_protection` in config, no step is emitted."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    cfg = _make_config(
        github={"enabled": True, "auth": "token", "repo": "o/r", "tag": "v1.0.0"}
    )
    report = run_bootstrap(cfg, apply=False)
    steps = report.target_outcomes["github"]
    assert not any(s.step == "branch_protection" for s in steps)


def test_bootstrap_skips_non_github_hosts(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """gitlab is a GitHost too but bootstrap is gated to GitHub for v0.1."""
    monkeypatch.setenv("GITLAB_TOKEN", "glpat_x")
    cfg = _make_config(
        gitlab={
            "enabled": True,
            "auth": "token",
            "project": "group/proj",
            "tag": "v1.0.0",
        }
    )
    report = run_bootstrap(cfg, apply=False)
    steps = report.target_outcomes["gitlab"]
    statuses = [s.status for s in steps]
    assert "skipped" in statuses


def test_bootstrap_no_topics_emits_no_topics_step(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    cfg = _make_config(github={"enabled": True, "auth": "token", "repo": "o/r", "tag": "v1.0.0"})
    report = run_bootstrap(cfg, apply=False)
    steps = report.target_outcomes["github"]
    # Only authenticate runs; no topics step (topics list empty).
    step_names = [s.step for s in steps]
    assert "topics" not in step_names


def test_bootstrap_ignores_registry_targets(clean_env: None) -> None:
    """Registry targets (non-GitHost) should be silently ignored."""
    cfg = _make_config(pypi={"enabled": True, "auth": "oidc", "package": "x"})
    report = run_bootstrap(cfg, apply=False)
    assert "pypi" not in report.target_outcomes


# ---------------------------------------------------------------------------
# rotate_tokens
# ---------------------------------------------------------------------------


def test_rotation_table_lookups() -> None:
    """Every known platform has a rotation step with a URL + keyring key."""
    for _slug, step in ROTATION_TABLE.items():
        assert step.token_management_url.startswith("https://")
        assert step.keyring_key
        assert step.env_var
        assert step.platform


def test_get_rotation_step_known() -> None:
    step = get_rotation_step("pypi")
    assert step.platform == "PyPI"
    assert "pypi.org" in step.token_management_url


def test_get_rotation_step_unknown_raises() -> None:
    with pytest.raises(KeyError, match="no rotation guidance"):
        get_rotation_step("does-not-exist")


def test_apply_rotation_writes_to_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    """apply_rotation calls set_keyring with the right key."""
    captured: dict[str, str] = {}

    def fake_set(key: str, value: str) -> None:
        captured["key"] = key
        captured["value"] = value

    monkeypatch.setattr("release_kit.workflows.rotate_tokens.set_keyring", fake_set)
    apply_rotation("pypi", "pypi-AgEI-secret")
    assert captured == {"key": "pypi", "value": "pypi-AgEI-secret"}


def test_apply_rotation_unknown_platform_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("release_kit.workflows.rotate_tokens.set_keyring", lambda k, v: None)
    with pytest.raises(KeyError, match="no rotation guidance"):
        apply_rotation("does-not-exist", "x")
