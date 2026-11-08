"""Security primitives for the Streamlit application.

These helpers are intentionally fail-closed. Import and use them from app.py when
migrating authentication, rendering, and encryption; they do not alter existing
application behavior until integrated.
"""

import hashlib
import hmac
import html
from typing import Optional, Tuple

import bcrypt
import streamlit as st
from cryptography.fernet import Fernet


def required_secret(name: str) -> str:
    """Return a configured secret or stop startup instead of using a fallback."""
    value = st.secrets.get(name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Required Streamlit secret {name!r} is not configured")
    return value.strip()


def fernet_from_secrets() -> Fernet:
    """Build Fernet only from the persistent deployment secret."""
    key = required_secret("FERNET_KEY").encode("utf-8")
    try:
        return Fernet(key)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("FERNET_KEY is not a valid Fernet key") from exc


def hash_password(password: str) -> str:
    """Hash a new password with bcrypt and a per-password random salt."""
    if not password:
        raise ValueError("Password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, stored_hash: str) -> Tuple[bool, Optional[str]]:
    """Verify bcrypt hashes; recognize legacy SHA-256 for gradual rehashing.

    Returns (valid, replacement_hash). A valid legacy hash returns a fresh
    bcrypt hash in replacement_hash so callers can persist it after login.
    """
    if not password or not stored_hash:
        return False, None
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii")), None
        except (ValueError, UnicodeEncodeError):
            return False, None
    if len(stored_hash) == 64:
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if hmac.compare_digest(stored_hash, legacy):
            return True, hash_password(password)
    return False, None


def escape_html(value: object) -> str:
    """Escape untrusted content before inserting into HTML text or attributes."""
    return html.escape(str(value if value is not None else ""), quote=True)
