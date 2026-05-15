"""Tests for the shared mixins.

Each mixin is tested in isolation via a minimal concrete subclass.
End-to-end tests for the platforms that compose them live alongside
each platform.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from release_kit.core.config import PolicyConfig
from release_kit.core.errors import (
    AuthenticationError,
    PlatformError,
    PublishError,
    ValidationError,
)
from release_kit.core.runner import RunContext
from release_kit.platforms.mixins.docker_push import DockerPushMixin
from release_kit.platforms.mixins.github_api import GitHubApiMixin
from release_kit.platforms.mixins.gitlab_api import GitLabApiMixin
from release_kit.platforms.mixins.npm_publish import NpmPublishMixin


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="x")


# --- DockerPushMixin ----------------------------------------------------


class _MiniDocker(DockerPushMixin):
    def __init__(self, login: list[str] | None, tags: list[str]) -> None:
        self._login = login
        self._tags = tags

    def _login_argv(self, ctx: RunContext) -> list[str] | None:
        return self._login

    def _image_reference(self, tag: str) -> str:
        return f"registry.example.com/me/img:{tag}"

    def _default_tags(self, ctx: RunContext) -> list[str]:
        return self._tags


def test_docker_publish_dry_run_no_subprocess() -> None:
    plat = _MiniDocker(login=["docker", "login", "-u", "x"], tags=["v1", "latest"])
    out = plat._do_publish(_ctx(dry_run=True))
    assert out.status == "dry-run"
    assert "2 tag(s)" in out.detail


def test_docker_publish_no_tags_raises() -> None:
    plat = _MiniDocker(login=None, tags=[])
    with pytest.raises(ValidationError) as exc:
        plat._do_publish(_ctx())
    assert exc.value.code == "no-tags"


# --- NpmPublishMixin ----------------------------------------------------


class _MiniNpm(NpmPublishMixin):
    def _npmrc_lines(self, ctx: RunContext) -> list[str]:
        return ["//registry.npmjs.org/:_authToken=x"]

    def _publish_args(self, ctx: RunContext) -> list[str]:
        return ["--access", "public"]


def test_npm_publish_dry_run() -> None:
    out = _MiniNpm()._do_publish(_ctx(dry_run=True))
    assert out.status == "dry-run"
    assert "npm publish" in out.detail


# --- GitHubApiMixin -----------------------------------------------------


class _MiniGitHub(GitHubApiMixin):
    pass


@respx.mock
def test_github_api_get_includes_auth_header(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    route = respx.get("https://api.github.com/repos/o/r").mock(
        return_value=httpx.Response(200, json={"name": "r"})
    )
    body = _MiniGitHub()._api_get(_ctx(), "/repos/o/r")
    assert body["name"] == "r"
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer ghp_x"
    assert sent.headers["accept"] == "application/vnd.github+json"


def test_github_api_missing_token_raises(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _MiniGitHub()._api_get(_ctx(), "/repos/o/r")
    assert exc.value.code == "token-not-found"


@respx.mock
def test_github_api_non2xx_raises_platform_error(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    respx.get("https://api.github.com/x").mock(return_value=httpx.Response(403, text="no"))
    with pytest.raises(PlatformError) as exc:
        _MiniGitHub()._api_get(_ctx(), "/x")
    assert exc.value.code == "github-api-error"


# --- GitLabApiMixin -----------------------------------------------------


class _MiniGitLab(GitLabApiMixin):
    pass


@respx.mock
def test_gitlab_api_uses_private_token_header(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat_x")
    route = respx.get("https://gitlab.com/api/v4/projects/1").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    _MiniGitLab()._api_get(_ctx(), "/projects/1")
    sent = route.calls.last.request
    assert sent.headers["private-token"] == "glpat_x"


def test_gitlab_api_missing_token_raises(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _MiniGitLab()._api_get(_ctx(), "/projects/1")
    assert exc.value.code == "token-not-found"


@respx.mock
def test_docker_login_failure_raises(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """When the configured login command exits non-zero, raise PublishError."""
    plat = _MiniDocker(login=["false"], tags=["v1"])
    with pytest.raises(PublishError) as exc:
        plat._do_publish(_ctx(dry_run=False))
    assert exc.value.code == "docker-login-failed"
