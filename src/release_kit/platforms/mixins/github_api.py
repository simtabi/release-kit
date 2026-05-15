"""GitHub REST API client mixin.

Shared by github.com, GitHub Enterprise Cloud, GitHub Enterprise
Server. Subclasses differ only in:

- ``api_base`` (e.g. ``https://api.github.com`` vs
  ``https://github.example.com/api/v3``).
- Whether OIDC is available.

Token resolution honours the standard release-kit chain. Operations
use httpx (sync, verify=True).
"""

from __future__ import annotations

import httpx

from ...core.errors import AuthenticationError, PlatformError
from ...core.runner import RunContext
from ...core.secrets import resolve_token


class GitHubApiMixin:
    """
    HTTP client + token resolution for any GitHub-protocol host.

    Subclasses set ``api_base`` (no trailing slash).
    """

    api_base: str = "https://api.github.com"

    def _client(self, ctx: RunContext, *, env_var: str = "GITHUB_TOKEN") -> httpx.Client:
        """
        Build an httpx.Client with auth, base URL, and the standard
        Accept header.

        @param  ctx
        @param  env_var  primary env var for the token resolution chain.
        @return httpx.Client  caller is responsible for ``.close()`` /
                              ``with`` block.
        @throws AuthenticationError  when no token resolves.
        """
        resolution = resolve_token("github", env_var=env_var)
        if not resolution.resolved:
            raise AuthenticationError(
                f"no GitHub token resolved (looked at {env_var}, RELEASE_KIT_TOKEN_GITHUB, keyring)",
                code="token-not-found",
                remediation=f"Set {env_var} in the environment.",
            )
        return httpx.Client(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {resolution.value}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "simtabi-release-kit",
            },
            timeout=30.0,
        )

    # ---- helpers ---------------------------------------------------------

    def _api_get(
        self, ctx: RunContext, path: str, *, env_var: str = "GITHUB_TOKEN"
    ) -> dict[str, object]:
        """
        GET ``path`` and return the JSON body.

        @param  path  begins with ``/`` (e.g. ``/repos/owner/repo``)
        @return dict
        @throws PlatformError on non-2xx.
        """
        with self._client(ctx, env_var=env_var) as client:
            r = client.get(path)
        if not r.is_success:
            raise PlatformError(
                f"GitHub API GET {path} returned {r.status_code}: {r.text[:200]}",
                code="github-api-error",
            )
        return r.json()  # type: ignore[no-any-return]

    def _api_post(
        self,
        ctx: RunContext,
        path: str,
        json: dict[str, object],
        *,
        env_var: str = "GITHUB_TOKEN",
    ) -> dict[str, object]:
        """POST + JSON body, returns parsed JSON response."""
        with self._client(ctx, env_var=env_var) as client:
            r = client.post(path, json=json)
        if not r.is_success:
            raise PlatformError(
                f"GitHub API POST {path} returned {r.status_code}: {r.text[:200]}",
                code="github-api-error",
            )
        return r.json()  # type: ignore[no-any-return]

    def _api_patch(
        self,
        ctx: RunContext,
        path: str,
        json: dict[str, object],
        *,
        env_var: str = "GITHUB_TOKEN",
    ) -> dict[str, object]:
        """PATCH + JSON body."""
        with self._client(ctx, env_var=env_var) as client:
            r = client.patch(path, json=json)
        if not r.is_success:
            raise PlatformError(
                f"GitHub API PATCH {path} returned {r.status_code}: {r.text[:200]}",
                code="github-api-error",
            )
        return r.json()  # type: ignore[no-any-return]

    def _api_put(
        self,
        ctx: RunContext,
        path: str,
        json: dict[str, object] | None = None,
        *,
        env_var: str = "GITHUB_TOKEN",
    )  -> dict[str, object] | None:
        """PUT + optional JSON body. 204 returns None."""
        with self._client(ctx, env_var=env_var) as client:
            r = client.put(path, json=json)
        if r.status_code == 204:
            return None
        if not r.is_success:
            raise PlatformError(
                f"GitHub API PUT {path} returned {r.status_code}: {r.text[:200]}",
                code="github-api-error",
            )
        return r.json()  # type: ignore[no-any-return]
