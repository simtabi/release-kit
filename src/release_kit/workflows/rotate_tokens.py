"""Interactive token rotation.

For each platform, walks a small wizard:
1. Open the token-management page in the user's browser.
2. Prompt for the new token (silent input).
3. Store via OS keyring.
4. Re-run a doctor probe to confirm the token works.

This module is the library entry point; the CLI provides the
prompt UI via Typer.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.logging import get_logger
from ..core.secrets import set_keyring

_log = get_logger(__name__)


@dataclass(frozen=True)
class RotationStep:
    """Per-platform rotation guidance: URL + the keyring slot to set."""

    platform: str
    token_management_url: str
    keyring_key: str
    env_var: str
    notes: str = ""


# Static table; could move to a JSON resource if the list grows.
ROTATION_TABLE: dict[str, RotationStep] = {
    "pypi": RotationStep(
        "PyPI",
        "https://pypi.org/manage/account/token/",
        "pypi",
        "PYPI_TOKEN",
        "Prefer per-project tokens. Rotate annually.",
    ),
    "npm": RotationStep(
        "npm",
        "https://www.npmjs.com/settings/your-username/tokens",
        "npm",
        "NPM_TOKEN",
        "Use Automation tokens for CI (bypasses 2FA OTP).",
    ),
    "dockerhub": RotationStep(
        "Docker Hub",
        "https://hub.docker.com/settings/security",
        "dockerhub",
        "DOCKERHUB_TOKEN",
        "Per-namespace access token, Read+Write+Delete.",
    ),
    "ghcr": RotationStep(
        "GHCR",
        "https://github.com/settings/tokens?type=beta",
        "ghcr",
        "GHCR_TOKEN",
        "Use fine-grained PAT with Packages: Read & write.",
    ),
    "github": RotationStep(
        "GitHub.com",
        "https://github.com/settings/tokens?type=beta",
        "github",
        "GITHUB_TOKEN",
        "Use fine-grained PAT, scoped per-repo.",
    ),
    "gitlab": RotationStep(
        "GitLab.com",
        "https://gitlab.com/-/user_settings/personal_access_tokens",
        "gitlab",
        "GITLAB_TOKEN",
        "Project / Group Access Tokens preferred over PAT.",
    ),
    "rubygems": RotationStep(
        "RubyGems",
        "https://rubygems.org/profile/api_keys",
        "rubygems",
        "RUBYGEMS_API_KEY",
        "Per-gem scope landed in 2023; use it.",
    ),
    "cargo": RotationStep(
        "crates.io",
        "https://crates.io/settings/tokens",
        "cargo",
        "CARGO_REGISTRY_TOKEN",
        "Per-crate scopes landed in 2023.",
    ),
    "nuget": RotationStep(
        "NuGet.org",
        "https://www.nuget.org/account/apikeys",
        "nuget",
        "NUGET_API_KEY",
        "Use glob-pattern scope to limit blast radius.",
    ),
    "packagist": RotationStep(
        "Packagist",
        "https://packagist.org/profile/",
        "packagist",
        "PACKAGIST_TOKEN",
        "Account-level; rotate annually.",
    ),
    "homebrew": RotationStep(
        "Homebrew tap",
        "https://github.com/settings/tokens?type=beta",
        "homebrew",
        "TAP_GITHUB_TOKEN",
        "Fine-grained PAT scoped to the tap repo.",
    ),
}


def get_rotation_step(platform: str) -> RotationStep:
    """Look up the rotation guidance for a platform slug."""
    if platform not in ROTATION_TABLE:
        raise KeyError(
            f"no rotation guidance for {platform!r}; " f"known: {sorted(ROTATION_TABLE)}"
        )
    return ROTATION_TABLE[platform]


def apply_rotation(platform: str, new_token: str) -> None:
    """
    Persist the new token to the OS keyring.

    Called by the CLI after the user has pasted the token. Doesn't
    touch the env var or `.env`; the keyring is the canonical place
    so the CLI's resolution chain finds it on the next run.

    @param  platform   slug.
    @param  new_token  the token value (already validated by the caller).
    """
    step = get_rotation_step(platform)
    set_keyring(step.keyring_key, new_token)
    _log.info("rotated", platform=platform, keyring_key=step.keyring_key)
