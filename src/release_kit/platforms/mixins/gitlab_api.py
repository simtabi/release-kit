"""GitLab REST API v4 client mixin.

Shared by gitlab.com and self-managed instances. Subclasses set
``api_base`` (e.g. ``https://gitlab.com`` or
``https://gitlab.example.com``); the mixin appends ``/api/v4``.
"""

from __future__ import annotations

import httpx

from ...core.errors import AuthenticationError, PlatformError
from ...core.runner import RunContext
from ...core.secrets import resolve_token


class GitLabApiMixin:
    """
    HTTP client + token resolution for any GitLab-protocol host.

    Subclasses set ``api_base`` (no trailing slash, no ``/api/v4``).
    """

    api_base: str = "https://gitlab.com"

    def _client(self, ctx: RunContext, *, env_var: str = "GITLAB_TOKEN") -> httpx.Client:
        """
        Build an httpx.Client with auth + base URL.

        GitLab accepts either ``PRIVATE-TOKEN: <pat>`` or
        ``Authorization: Bearer <oauth-token>``; we use ``PRIVATE-TOKEN``
        because it works for both PAT and Project / Group Access
        Tokens, which is the dominant pattern.

        @param  ctx
        @param  env_var  primary env var to try.
        @return httpx.Client
        @throws AuthenticationError when no token resolves.
        """
        resolution = resolve_token("gitlab", env_var=env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no GitLab token resolved (looked at {env_var}, RELEASE_KIT_TOKEN_GITLAB, keyring)",
                code="token-not-found",
                remediation=f"Set {env_var} in the environment.",
            )
        return httpx.Client(
            base_url=f"{self.api_base}/api/v4",
            headers={
                "PRIVATE-TOKEN": str(resolution.value),
                "User-Agent": "simtabi-release-kit",
            },
            timeout=30.0,
        )

    def _api_get(
        self, ctx: RunContext, path: str, *, env_var: str = "GITLAB_TOKEN"
    ) -> dict[str, object]:
        """GET ``path``; returns parsed JSON."""
        with self._client(ctx, env_var=env_var) as client:
            r = client.get(path)
        if not r.is_success:
            raise PlatformError(
                f"GitLab API GET {path} returned {r.status_code}: {r.text[:200]}",
                code="gitlab-api-error",
            )
        return r.json()  # type: ignore[no-any-return]

    def _api_post(
        self,
        ctx: RunContext,
        path: str,
        json: dict[str, object],
        *,
        env_var: str = "GITLAB_TOKEN",
    ) -> dict[str, object]:
        with self._client(ctx, env_var=env_var) as client:
            r = client.post(path, json=json)
        if not r.is_success:
            raise PlatformError(
                f"GitLab API POST {path} returned {r.status_code}: {r.text[:200]}",
                code="gitlab-api-error",
            )
        return r.json()  # type: ignore[no-any-return]
