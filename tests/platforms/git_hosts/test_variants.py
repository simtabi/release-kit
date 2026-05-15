"""Tests for the git-host variants beyond github.com / gitlab.com."""

from __future__ import annotations

import httpx
import pytest
import respx

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError, PublishError
from release_kit.core.runner import RunContext
from release_kit.platforms.git_hosts.azure_devops import AzureDevOps
from release_kit.platforms.git_hosts.bitbucket import BitbucketCloud
from release_kit.platforms.git_hosts.bitbucket_dc import BitbucketDataCenter
from release_kit.platforms.git_hosts.gitea import Gitea
from release_kit.platforms.git_hosts.github_enterprise import (
    GitHubEnterpriseCloud,
    GitHubEnterpriseServer,
)
from release_kit.platforms.git_hosts.gitlab_self_managed import GitLabSelfManaged


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="x")


def _build(cls, **extras):
    target = TargetConfig.model_validate({"enabled": True, "auth": "token", **extras})
    plat = cls.from_target(target)
    plat.__post_init__()
    return plat


# --- GHEC ------------------------------------------------------------------


def test_ghec_inherits_github_flow(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    out = _build(GitHubEnterpriseCloud, repo="o/r").authenticate(_ctx())
    assert out.status == "ok"


# --- GHES ------------------------------------------------------------------


def test_ghes_host_sets_api_base(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    plat = _build(GitHubEnterpriseServer, repo="o/r", host="github.example.com")
    assert plat.api_base == "https://github.example.com/api/v3"
    out = plat.authenticate(_ctx())
    assert out.status == "ok"


# --- GitLab self-managed ---------------------------------------------------


def test_gitlab_self_managed_host(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "glpat_x")
    plat = _build(GitLabSelfManaged, project="g/p", host="gitlab.example.com")
    assert plat.api_base == "https://gitlab.example.com"
    out = plat.authenticate(_ctx())
    assert out.status == "ok"


# --- Bitbucket Cloud -------------------------------------------------------


def test_bitbucket_missing_workspace(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(BitbucketCloud).authenticate(_ctx())
    assert exc.value.code == "missing-config"


def test_bitbucket_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "p")
    out = _build(BitbucketCloud, workspace="w", repo="r", username="u").authenticate(_ctx())
    assert out.status == "ok"


@respx.mock
def test_bitbucket_publish_404_raises(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "p")
    plat = _build(BitbucketCloud, workspace="w", repo="r", username="u", tag="v1")
    plat.authenticate(_ctx())
    respx.get("https://api.bitbucket.org/2.0/repositories/w/r/refs/tags/v1").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(PublishError) as exc:
        plat.publish(_ctx(dry_run=False))
    assert exc.value.code == "tag-not-pushed"


# --- Bitbucket DC ----------------------------------------------------------


def test_bitbucket_dc_missing_host(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(BitbucketDataCenter).authenticate(_ctx())
    assert exc.value.code == "missing-host"


def test_bitbucket_dc_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BITBUCKET_DC_TOKEN", "t")
    out = _build(BitbucketDataCenter, host="bb.example.com", project="P", repo="r").authenticate(
        _ctx()
    )
    assert out.status == "ok"


# --- Gitea -----------------------------------------------------------------


def test_gitea_missing_host(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(Gitea).authenticate(_ctx())
    assert exc.value.code == "missing-host"


def test_gitea_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITEA_TOKEN", "t")
    out = _build(Gitea, host="codeberg.org", owner="o", repo="r").authenticate(_ctx())
    assert out.status == "ok"


@respx.mock
def test_gitea_publish_apply(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITEA_TOKEN", "t")
    plat = _build(Gitea, host="codeberg.org", owner="o", repo="r", tag="v1")
    plat.authenticate(_ctx())
    route = respx.post("https://codeberg.org/api/v1/repos/o/r/releases").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    out = plat.publish(_ctx(dry_run=False))
    assert route.called
    assert out.status == "ok"


# --- Azure DevOps ----------------------------------------------------------


def test_azure_devops_missing_config(clean_env: None) -> None:
    with pytest.raises(AuthenticationError) as exc:
        _build(AzureDevOps, organization="o").authenticate(_ctx())
    assert exc.value.code == "missing-config"


def test_azure_devops_validate_needs_sha(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")
    plat = _build(AzureDevOps, organization="o", project="p", repo="r", tag="v1")
    plat.authenticate(_ctx())
    with pytest.raises(AuthenticationError) as exc:
        plat.validate(_ctx())
    assert exc.value.code == "missing-sha"


def test_azure_devops_validate_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "p")
    plat = _build(
        AzureDevOps,
        organization="o",
        project="p",
        repo="r",
        tag="v1",
        commit_sha="abc123def456",
    )
    plat.authenticate(_ctx())
    out = plat.validate(_ctx())
    assert out.status == "ok"
