"""``.env`` loader.

Thin wrapper over python-dotenv with a couple of policies:

- Refuses to load `.env` files that are world-readable (mode > 0644).
- Doesn't override env vars already set in the process (so CI
  secrets always win).
- Returns a typed dict so callers can pass it explicitly.

The module never logs values. Use :py:func:`logging.redact_token`
to surface presence-without-leak in audit trails.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from dotenv import dotenv_values

from .errors import ConfigError
from .logging import get_logger

_log = get_logger(__name__)


def load_env_file(
    path: str | Path | None = None,
    *,
    override: bool = False,
) -> dict[str, str]:
    """
    Read a ``.env`` file into a dict.

    Lookup order when ``path`` is None:

    1. ``$RELEASE_KIT_ENV_FILE``
    2. ``./.env``
    3. ``~/.config/release-kit/.env``

    Returns an empty dict when no file is found (not an error).
    Raises when a found file has insecure permissions.

    @param  path      explicit path, or None for the search order above.
    @param  override  if True, env-var keys already set in ``os.environ``
                      are overwritten by the file. Default False.
    @return           dict[str, str] of resolved key-value pairs.
    @throws ConfigError  on world-readable file.
    """
    candidate = _resolve_path(path)
    if candidate is None or not candidate.is_file():
        return {}

    _enforce_secure_mode(candidate)

    parsed: dict[str, str] = {
        k: v for k, v in dotenv_values(candidate).items() if v is not None
    }
    if override:
        for k, v in parsed.items():
            os.environ[k] = v
    else:
        for k, v in parsed.items():
            os.environ.setdefault(k, v)

    _log.info("env-file-loaded", path=str(candidate), count=len(parsed))
    return parsed


def _resolve_path(path: str | Path | None) -> Path | None:
    """Resolve the search order described in ``load_env_file``."""
    if path is not None:
        return Path(path).expanduser()
    env_override = os.environ.get("RELEASE_KIT_ENV_FILE")
    if env_override:
        return Path(env_override).expanduser()
    local = Path(".env")
    if local.is_file():
        return local
    user = Path.home() / ".config" / "release-kit" / ".env"
    if user.is_file():
        return user
    return None


def _enforce_secure_mode(path: Path) -> None:
    """
    Raise ConfigError if the file is group/world-readable.

    On Windows ``os.stat`` mode bits are unreliable; this check is a
    no-op there. On Unix, anything wider than ``0o600`` for a file
    in the user's HOME, or wider than ``0o644`` in a repo, is
    flagged. We use 0o644 as the soft ceiling for repo-local `.env`
    because some setups (Docker bind-mounts) reset modes.
    """
    if os.name != "posix":  # pragma: no cover
        return
    st = path.stat()
    mode = stat.S_IMODE(st.st_mode)
    # Group / others must not have read or write.
    if mode & 0o077:
        raise ConfigError(
            f".env file {path} has insecure mode {oct(mode)}",
            code="env-insecure-mode",
            remediation=f"chmod 600 {path}",
        )
