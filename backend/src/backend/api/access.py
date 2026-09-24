"""Optional shared-password protection for a small private deployment."""

from __future__ import annotations

import hashlib
import hmac
import os
import time


SESSION_COOKIE_NAME = "cre_access"
SESSION_LIFETIME_SECONDS = 60 * 60 * 12


def access_is_required() -> bool:
    return os.getenv("APP_REQUIRE_AUTH", "false").lower() in {"1", "true", "yes"}


def validate_access_configuration() -> None:
    """Fail closed when a protected deployment is missing either secret."""
    if access_is_required() and (not os.getenv("APP_ACCESS_PASSWORD") or not os.getenv("APP_SESSION_SECRET")):
        raise RuntimeError("APP_ACCESS_PASSWORD and APP_SESSION_SECRET are required when APP_REQUIRE_AUTH is enabled")


def password_is_valid(password: str) -> bool:
    expected_password = os.getenv("APP_ACCESS_PASSWORD", "")
    return bool(expected_password) and hmac.compare_digest(password, expected_password)


def create_session_token() -> str:
    expires_at = str(int(time.time()) + SESSION_LIFETIME_SECONDS)
    signature = _signature(expires_at)
    return f"{expires_at}.{signature}"


def session_is_valid(token: str | None) -> bool:
    if not token:
        return False
    expires_at, separator, signature = token.partition(".")
    if not separator or not expires_at.isdecimal() or int(expires_at) < int(time.time()):
        return False
    return hmac.compare_digest(signature, _signature(expires_at))


def cookie_requires_https() -> bool:
    return os.getenv("APP_SESSION_COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}


def _signature(value: str) -> str:
    secret = os.getenv("APP_SESSION_SECRET", "")
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
