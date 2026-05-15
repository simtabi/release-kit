"""Tests for the Docker-protocol registries (besides Docker Hub + GHCR)."""

from __future__ import annotations

import pytest

from release_kit.core.config import PolicyConfig, TargetConfig
from release_kit.core.errors import AuthenticationError
from release_kit.core.runner import RunContext
from release_kit.platforms.registries.acr import AzureContainerRegistry
from release_kit.platforms.registries.aws_ecr import AWSElasticContainerRegistry
from release_kit.platforms.registries.gar import GoogleArtifactRegistry
from release_kit.platforms.registries.gitlab_registry import GitLabRegistry


def _ctx(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, policies=PolicyConfig(), target_name="x")


def _build(cls, **extras):
    target = TargetConfig.model_validate({"enabled": True, "auth": "token", **extras})
    plat = cls.from_target(target)
    plat.__post_init__()
    return plat


# --- GitLab Container Registry --------------------------------------------


def test_gitlab_registry_missing_image(clean_env: None) -> None:
    plat = _build(GitLabRegistry)
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "missing-image"


def test_gitlab_registry_missing_token(clean_env: None) -> None:
    plat = _build(GitLabRegistry, image="registry.gitlab.com/g/p")
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "token-not-found"


def test_gitlab_registry_ok(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITLAB_REGISTRY_TOKEN", "glpat_x")
    plat = _build(GitLabRegistry, image="registry.gitlab.com/g/p")
    out = plat.authenticate(_ctx())
    assert out.status == "ok"


def test_gitlab_registry_image_ref() -> None:
    plat = _build(GitLabRegistry, image="registry.gitlab.com/g/p")
    assert plat._image_reference("v1") == "registry.gitlab.com/g/p:v1"


# --- AWS ECR --------------------------------------------------------------


def test_aws_ecr_missing_registry(clean_env: None) -> None:
    plat = _build(AWSElasticContainerRegistry, image="release-kit")
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "missing-registry"


def test_aws_ecr_missing_image(clean_env: None) -> None:
    plat = _build(AWSElasticContainerRegistry, registry="123.dkr.ecr.us-east-1.amazonaws.com")
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "missing-image"


def test_aws_ecr_image_ref() -> None:
    plat = _build(
        AWSElasticContainerRegistry,
        registry="123.dkr.ecr.us-east-1.amazonaws.com",
        image="release-kit",
    )
    assert (
        plat._image_reference("v1")
        == "123.dkr.ecr.us-east-1.amazonaws.com/release-kit:v1"
    )


# --- GAR ------------------------------------------------------------------


def test_gar_requires_all_four_keys(clean_env: None) -> None:
    plat = _build(GoogleArtifactRegistry, registry="us-central1-docker.pkg.dev")
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "missing-config"


def test_gar_image_ref() -> None:
    plat = _build(
        GoogleArtifactRegistry,
        registry="us-central1-docker.pkg.dev",
        project="my-proj",
        repo="my-repo",
        image="release-kit",
    )
    assert (
        plat._image_reference("v1")
        == "us-central1-docker.pkg.dev/my-proj/my-repo/release-kit:v1"
    )


# --- ACR ------------------------------------------------------------------


def test_acr_missing_registry(clean_env: None) -> None:
    plat = _build(AzureContainerRegistry, image="release-kit")
    with pytest.raises(AuthenticationError) as exc:
        plat.authenticate(_ctx())
    assert exc.value.code == "missing-registry"


def test_acr_image_ref() -> None:
    plat = _build(AzureContainerRegistry, registry="myreg", image="release-kit")
    assert plat._image_reference("v1") == "myreg.azurecr.io/release-kit:v1"


def test_acr_publish_dry_run() -> None:
    plat = _build(AzureContainerRegistry, registry="myreg", image="x", tags=["v1"])
    out = plat.publish(_ctx())
    assert out.status == "dry-run"
