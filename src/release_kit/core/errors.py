"""Typed exception hierarchy.

Every error raised by release-kit subclasses :class:`ReleaseKitError`.
Library callers can catch the base class and check ``.code`` /
``.remediation`` for structured handling.

The hierarchy is intentionally shallow:

- ``ReleaseKitError`` (base)
  - ``ConfigError``         schema / model violations
  - ``ValidationError``     preflight failures (clean git, tag match, ...)
  - ``AuthenticationError`` token / credential problems
  - ``PlatformError``       generic per-platform failure
    - ``PublishError``      publish step failed
    - ``VerifyError``       post-publish verification failed
"""

from __future__ import annotations


class ReleaseKitError(Exception):
    """
    Base class for every release-kit exception.

    Carries an optional ``code`` for programmatic dispatch and a
    ``remediation`` hint for the user. Both are surfaced by the
    CLI's error formatter.

    @param  message      Human-readable failure description.
    @param  code         Short machine slug (e.g. ``"missing-token"``).
    @param  remediation  One-line "what to do next" hint.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        remediation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.remediation = remediation

    def __str__(self) -> str:
        parts: list[str] = [super().__str__()]
        if self.remediation:
            parts.append(f"  remediation: {self.remediation}")
        return "\n".join(parts)


class ConfigError(ReleaseKitError):
    """
    Raised when the JSON config violates the schema or references
    something the loader can't resolve.

    @code   config-invalid
    """


class ValidationError(ReleaseKitError):
    """
    Raised by the preflight check when a policy is violated.

    Examples: dirty working tree, tag mismatch, missing CHANGELOG.

    @code   preflight-failed
    """


class AuthenticationError(ReleaseKitError):
    """
    Raised when a target's credentials can't be resolved or are
    rejected by the registry.

    @code   auth-failed
    """


class PlatformError(ReleaseKitError):
    """
    Generic per-platform failure. Prefer the more specific
    subclasses where the failure mode is clear.

    @code   platform-error
    """


class PublishError(PlatformError):
    """
    Raised when the publish step itself fails (upload rejected,
    network error after retries, registry returned non-2xx).

    @code   publish-failed
    """


class VerifyError(PlatformError):
    """
    Raised when post-publish verification fails (artifact not
    findable on the registry, version mismatch).

    @code   verify-failed
    """
