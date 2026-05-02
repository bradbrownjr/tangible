"""Password hashing and secret-key loading."""

from __future__ import annotations

import secrets
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def load_or_create_secret_key(provided: str | None, config_dir: Path) -> str:
    """Return the secret key, persisting a generated value when needed."""
    if provided:
        return provided
    config_dir.mkdir(parents=True, exist_ok=True)
    key_path = config_dir / "secret.key"
    if key_path.is_file():
        text = key_path.read_text(encoding="utf-8").strip()
        if text:
            return text
    import contextlib

    key = secrets.token_urlsafe(64)
    key_path.write_text(key + "\n", encoding="utf-8")
    with contextlib.suppress(OSError):
        key_path.chmod(0o600)
    return key


def generate_token() -> str:
    """Generate an opaque API token / share slug."""
    return secrets.token_urlsafe(32)
