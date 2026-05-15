"""Shared pytest fixtures."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path

import pytest

from release_kit.core.config import Config


@pytest.fixture
def example_config_dict() -> dict:
    """A minimal valid config dict that satisfies the schema."""
    return Config.example()


@pytest.fixture
def example_config(example_config_dict: dict, tmp_path: Path) -> Path:
    """Write the example config to a temp path and return the path."""
    out = tmp_path / "release.json"
    out.write_text(json.dumps(example_config_dict), encoding="utf-8")
    return out


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Strip release-kit related env vars so tests start from a known state."""
    for k in list(os.environ):
        if k.startswith(("PYPI_", "NPM_", "DOCKERHUB_", "RELEASE_KIT_")):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITLAB_CI", raising=False)
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", raising=False)
    return
