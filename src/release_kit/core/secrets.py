"""Token resolution chain.

When a platform needs a credential, it asks
:func:`resolve_token` with:

- the ``key`` (a stable identifier like ``"pypi"`` or ``"github"``);
- the ``env_var`` it expects;
- optionally an explicit ``override`` value.

Resolution order (highest precedence first):

1. ``override`` (explicit kwarg from the caller / CLI flag).
2. ``os.environ[env_var]``.
3. ``os.environ["RELEASE_KIT_TOKEN_<KEY>"]`` (generic fallback).
4. OS keyring entry under service ``release-kit:<key>``.
5. ``None``.

The chain never logs values. Audit trail records the **source**
that resolved (env var name, keyring entry, "override") so
operators can answer "where did this token come from?" without
the value ever leaving memory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .logging import get_logger, redact_token

_log = get_logger(__name__)

KEYRING_SERVICE = "release-kit"


@dataclass(frozen=True)
class TokenResolution:
    """
    Where a token came from + its redacted preview.

    @field  value     The resolved token. ``None`` if nothing matched.
    @field  source    Human description of the source ("env:PYPI_TOKEN",
                      "keyring:release-kit:pypi", "override").
    @field  preview   Redacted preview for logging via
                      :py:func:`~release_kit.core.logging.redact_token`.
    """

    value: str | None
    source: str
    preview: str

    @property
    def resolved(self) -> bool:
        return self.value is not None


def resolve_token(
    key: str,
    *,
    env_var: str | None = None,
    override: str | None = None,
) -> TokenResolution:
    """
    Walk the resolution chain and return how the token was resolved.

    @param  key       stable identifier; controls the keyring entry name
                      and the ``RELEASE_KIT_TOKEN_<KEY>`` fallback var.
    @param  env_var   primary env var to try (e.g., ``PYPI_TOKEN``).
    @param  override  explicit value (highest precedence; usually a CLI flag).
    @return TokenResolution
    """
    if override:
        return TokenResolution(
            value=override,
            source="override",
            preview=redact_token(override),
        )

    if env_var:
        val = os.environ.get(env_var)
        if val:
            return TokenResolution(
                value=val,
                source=f"env:{env_var}",
                preview=redact_token(val),
            )

    fallback_env = f"RELEASE_KIT_TOKEN_{key.upper().replace('-', '_')}"
    val = os.environ.get(fallback_env)
    if val:
        return TokenResolution(
            value=val,
            source=f"env:{fallback_env}",
            preview=redact_token(val),
        )

    keyring_value = _try_keyring(key)
    if keyring_value:
        return TokenResolution(
            value=keyring_value,
            source=f"keyring:{KEYRING_SERVICE}:{key}",
            preview=redact_token(keyring_value),
        )

    return TokenResolution(value=None, source="none", preview="")


def _try_keyring(key: str) -> str | None:
    """
    Best-effort keyring lookup.

    The ``keyring`` library can raise on systems without a backend
    (headless Linux without a secret-service daemon). We swallow
    the error and return None; operators on such systems fall back
    to env vars or `.env`.
    """
    try:
        import keyring  # local import: optional dep on some installs
    except ImportError:  # pragma: no cover
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, key)
    except Exception as e:  # pragma: no cover
        _log.debug("keyring-lookup-failed", key=key, error=str(e))
        return None


def set_keyring(key: str, value: str) -> None:
    """
    Store a token in the OS keyring under the release-kit service.

    Used by ``release-kit rotate-tokens``; not part of the publish
    hot path. Raises on backend failure (operators should know).

    @param  key    stable identifier (matches ``resolve_token`` lookup).
    @param  value  the secret.
    """
    import keyring
    keyring.set_password(KEYRING_SERVICE, key, value)
    _log.info("keyring-set", key=key, preview=redact_token(value))


def delete_keyring(key: str) -> None:
    """
    Remove a token from the OS keyring.

    Idempotent: missing entry is not an error.
    """
    import keyring
    try:
        keyring.delete_password(KEYRING_SERVICE, key)
        _log.info("keyring-delete", key=key)
    except keyring.errors.PasswordDeleteError:
        _log.info("keyring-delete-noop", key=key)
