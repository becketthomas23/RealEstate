"""Account-based access control for a private Deal Scope deployment.

Users live in the ``users`` table with PBKDF2-SHA256 password hashes. A
signed, expiring cookie carries the user id; the middleware resolves it on
every request so handlers can record who did what. Authentication is enabled
with ``APP_REQUIRE_AUTH=true`` and the first administrator is bootstrapped
from ``APP_ADMIN_EMAIL`` / ``APP_ADMIN_PASSWORD`` when no users exist.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time


SESSION_COOKIE_NAME = "dealscope_session"
SESSION_LIFETIME_SECONDS = 60 * 60 * 12
PBKDF2_ITERATIONS = 390_000
MINIMUM_PASSWORD_LENGTH = 8


def access_is_required() -> bool:
    return os.getenv("APP_REQUIRE_AUTH", "false").lower() in {"1", "true", "yes"}


def bootstrap_admin() -> tuple[str, str, str] | None:
    """Return (email, name, password) for the first administrator, if configured."""
    email = os.getenv("APP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("APP_ADMIN_PASSWORD", "")
    if not email or not password:
        return None
    return email, os.getenv("APP_ADMIN_NAME", "Administrator").strip() or "Administrator", password


def validate_access_configuration() -> None:
    """Fail closed when a protected deployment is missing the session secret."""
    if access_is_required() and not os.getenv("APP_SESSION_SECRET"):
        raise RuntimeError("APP_SESSION_SECRET is required when APP_REQUIRE_AUTH is enabled")


def hash_password(password: str) -> str:
    if len(password) < MINIMUM_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MINIMUM_PASSWORD_LENGTH} characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def password_matches(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(iterations))
        return hmac.compare_digest(candidate, _unb64(digest))
    except (ValueError, TypeError):
        return False


def create_session_token(user_id: str) -> str:
    expires_at = str(int(time.time()) + SESSION_LIFETIME_SECONDS)
    payload = f"{user_id}.{expires_at}"
    return f"{payload}.{_signature(payload)}"


def session_user_id(token: str | None) -> str | None:
    """Return the user id carried by a valid, unexpired token."""
    if not token:
        return None
    try:
        user_id, expires_at, signature = token.rsplit(".", 2)
    except ValueError:
        return None
    if not user_id or not expires_at.isdecimal() or int(expires_at) < int(time.time()):
        return None
    if not hmac.compare_digest(signature, _signature(f"{user_id}.{expires_at}")):
        return None
    return user_id


def cookie_requires_https() -> bool:
    return os.getenv("APP_SESSION_COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}


def _signature(value: str) -> str:
    secret = os.getenv("APP_SESSION_SECRET", "")
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
