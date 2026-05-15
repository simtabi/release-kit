"""GitHub Enterprise Cloud + Server publishers.

Both reuse the github.GitHub flow with overridden ``api_base``.
@see  docs/playbook/git-hosts/github-enterprise-cloud.md
       docs/playbook/git-hosts/github-enterprise-server.md
"""

from __future__ import annotations

from typing import ClassVar

from ..base import AuthMethod, AutomationLevel
from .github import GitHub


class GitHubEnterpriseCloud(GitHub):
    """GHEC: SaaS GitHub Enterprise. Same hostnames as github.com."""

    slug: ClassVar[str] = "github-enterprise-cloud"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC, AuthMethod.TOKEN,
    )
    # api_base inherited from GitHub (api.github.com); EMU + SAML SSO
    # are handled at the GitHub side (PAT must be SSO-authorised).


class GitHubEnterpriseServer(GitHub):
    """
    GHES: self-hosted GitHub Enterprise appliance.

    Config keys (under ``targets.github-enterprise-server``)::

        "host":  "github.example.com"     # required
        # plus the standard GitHub keys (repo, tag, ...)
    """

    slug: ClassVar[str] = "github-enterprise-server"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.FULL_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC, AuthMethod.TOKEN,
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        extras = self.target.model_extra or {}
        host = str(extras.get("host", "")).rstrip("/")
        if not host:
            # Defer the host validation to authenticate() so __post_init__
            # never raises (matches the pattern in other platforms).
            self._host = ""
            self.api_base = "https://api.github.com"
        else:
            self._host = host
            self.api_base = f"https://{host}/api/v3"
