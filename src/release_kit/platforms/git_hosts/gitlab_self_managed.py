"""GitLab Self-Managed publisher.

@see  docs/playbook/git-hosts/gitlab-self-managed.md
"""

from __future__ import annotations

from typing import ClassVar

from ..base import AuthMethod, AutomationLevel
from .gitlab import GitLab


class GitLabSelfManaged(GitLab):
    """
    Self-hosted GitLab instance.

    Config adds ``host`` (without scheme); inherits everything else
    from gitlab.GitLab.

    Config keys (under ``targets.gitlab-self-managed``)::

        "host":  "gitlab.example.com"
        # plus the standard GitLab keys (project, tag, ...)
    """

    slug: ClassVar[str] = "gitlab-self-managed"
    automation_level: ClassVar[AutomationLevel] = AutomationLevel.OIDC_API
    supported_auth_methods: ClassVar[tuple[AuthMethod, ...]] = (
        AuthMethod.OIDC,
        AuthMethod.TOKEN,
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        extras = self.target.model_extra or {}
        host = str(extras.get("host", "")).rstrip("/")
        if host:
            self.api_base = f"https://{host}"
