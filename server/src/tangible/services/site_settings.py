"""Site-level settings: admin-managed DB overrides on top of env/default values.

Resolution order (highest to lowest):
  1. DB override stored in ``app_settings``
  2. Environment variable (TANGIBLE_* or set via YAML overlay)
  3. Hardcoded default

Sensitive fields are returned as ``"***"`` in the read API to avoid leaking
secrets. Passing ``"***"`` in a PUT request means "leave unchanged".
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session as DBSession

from tangible.config import Settings
from tangible.models.app_setting import AppSetting

# --- Registry ---------------------------------------------------------------

class _Meta:
    __slots__ = ("default", "description", "env_attr", "env_var", "section", "sensitive", "type")

    def __init__(
        self,
        *,
        type: str,
        env_attr: str | None,
        env_var: str | None,
        default: Any,
        description: str,
        sensitive: bool,
        section: str,
    ) -> None:
        self.type = type
        self.env_attr = env_attr
        self.env_var = env_var
        self.default = default
        self.description = description
        self.sensitive = sensitive
        self.section = section


MANAGED_SETTINGS: dict[str, _Meta] = {
    # --- Security ---
    "require_2fa": _Meta(
        type="bool",
        env_attr="require_2fa",
        env_var="TANGIBLE_REQUIRE_2FA",
        default=False,
        description="Require all users to enroll in two-factor authentication before they can access the app",
        sensitive=False,
        section="security",
    ),
    "registration_enabled": _Meta(
        type="bool",
        env_attr="registration_enabled",
        env_var="TANGIBLE_REGISTRATION_ENABLED",
        default=True,
        description="Allow new users to self-register",
        sensitive=False,
        section="security",
    ),
    "password_min_length": _Meta(
        type="int",
        env_attr="password_min_length",
        env_var="TANGIBLE_PASSWORD_MIN_LENGTH",
        default=12,
        description="Minimum password length for new or changed passwords",
        sensitive=False,
        section="security",
    ),
    # --- Sessions ---
    "session_ttl_hours": _Meta(
        type="int",
        env_attr="session_ttl_hours",
        env_var="TANGIBLE_SESSION_TTL_HOURS",
        default=720,
        description="How long a browser login session stays valid (hours; 720 = 30 days)",
        sensitive=False,
        section="sessions",
    ),
    # --- Integrations ---
    "discogs_token": _Meta(
        type="str",
        env_attr="discogs_token",
        env_var="TANGIBLE_DISCOGS_TOKEN",
        default=None,
        description="Discogs personal access token for vinyl/record metadata lookups",
        sensitive=True,
        section="integrations",
    ),
    "tmdb_api_key": _Meta(
        type="str",
        env_attr="tmdb_api_key",
        env_var="TANGIBLE_TMDB_API_KEY",
        default=None,
        description="The Movie Database (TMDb) API key for movie and TV metadata",
        sensitive=True,
        section="integrations",
    ),
    "igdb_client_id": _Meta(
        type="str",
        env_attr="igdb_client_id",
        env_var="TANGIBLE_IGDB_CLIENT_ID",
        default=None,
        description="IGDB (Twitch Developer) client ID for video game metadata",
        sensitive=False,
        section="integrations",
    ),
    "igdb_client_secret": _Meta(
        type="str",
        env_attr="igdb_client_secret",
        env_var="TANGIBLE_IGDB_CLIENT_SECRET",
        default=None,
        description="IGDB (Twitch Developer) client secret for video game metadata",
        sensitive=True,
        section="integrations",
    ),
    "upcitemdb_key": _Meta(
        type="str",
        env_attr="upcitemdb_key",
        env_var="TANGIBLE_UPCITEMDB_KEY",
        default=None,
        description="UPCitemdb API key for barcode product lookups",
        sensitive=True,
        section="integrations",
    ),
    "google_books_api_key": _Meta(
        type="str",
        env_attr="google_books_api_key",
        env_var="TANGIBLE_GOOGLE_BOOKS_API_KEY",
        default=None,
        description="Google Books API key for book metadata lookups",
        sensitive=True,
        section="integrations",
    ),
    # --- Email / SMTP ---
    "smtp_host": _Meta(
        type="str",
        env_attr="smtp_host",
        env_var="TANGIBLE_SMTP_HOST",
        default=None,
        description="SMTP server hostname for outgoing email notifications",
        sensitive=False,
        section="email",
    ),
    "smtp_port": _Meta(
        type="int",
        env_attr="smtp_port",
        env_var="TANGIBLE_SMTP_PORT",
        default=587,
        description="SMTP server port (default 587 for STARTTLS)",
        sensitive=False,
        section="email",
    ),
    "smtp_user": _Meta(
        type="str",
        env_attr="smtp_user",
        env_var="TANGIBLE_SMTP_USER",
        default=None,
        description="SMTP login username",
        sensitive=False,
        section="email",
    ),
    "smtp_password": _Meta(
        type="str",
        env_attr="smtp_password",
        env_var="TANGIBLE_SMTP_PASSWORD",
        default=None,
        description="SMTP login password",
        sensitive=True,
        section="email",
    ),
    "smtp_from": _Meta(
        type="str",
        env_attr="smtp_from",
        env_var="TANGIBLE_SMTP_FROM",
        default=None,
        description="From address used on outgoing emails (e.g. tangible@example.com)",
        sensitive=False,
        section="email",
    ),
    "smtp_starttls": _Meta(
        type="bool",
        env_attr="smtp_starttls",
        env_var="TANGIBLE_SMTP_STARTTLS",
        default=True,
        description="Use STARTTLS when connecting to the SMTP server",
        sensitive=False,
        section="email",
    ),
}


# --- Internal helpers -------------------------------------------------------

def _parse(raw: str, type_: str) -> Any:
    if type_ == "bool":
        return raw.lower() in ("1", "true", "yes", "on")
    if type_ == "int":
        return int(raw)
    return raw or None  # empty string → None for str fields


def _serialize(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _env_source(meta: _Meta) -> str:
    """Return 'environment' if the corresponding env var is explicitly set."""
    if meta.env_var and os.environ.get(meta.env_var) is not None:
        return "environment"
    return "default"


def _effective(meta: _Meta, settings: Settings) -> Any:
    """Return the non-DB effective value for a setting."""
    if meta.env_attr is not None:
        return getattr(settings, meta.env_attr, meta.default)
    return meta.default


# --- Public API -------------------------------------------------------------

def get_site_bool(db: DBSession, key: str, settings: Settings) -> bool:
    """Return the effective boolean value for a site setting (DB > env > default)."""
    row = db.get(AppSetting, key)
    if row is not None:
        return _parse(row.value, "bool")
    meta = MANAGED_SETTINGS.get(key)
    if meta is None:
        return False
    return bool(_effective(meta, settings))


def get_site_int(db: DBSession, key: str, settings: Settings) -> int:
    """Return the effective integer value for a site setting."""
    row = db.get(AppSetting, key)
    if row is not None:
        return _parse(row.value, "int")
    meta = MANAGED_SETTINGS.get(key)
    if meta is None:
        return 0
    return int(_effective(meta, settings) or 0)


def get_site_str(db: DBSession, key: str, settings: Settings) -> str | None:
    """Return the effective string value for a site setting."""
    row = db.get(AppSetting, key)
    if row is not None:
        v = _parse(row.value, "str")
        return v or None
    meta = MANAGED_SETTINGS.get(key)
    if meta is None:
        return None
    v = _effective(meta, settings)
    return str(v) if v is not None else None


def list_site_settings(db: DBSession, settings: Settings) -> list[dict]:
    """Return all managed settings with their current values and source labels."""
    db_rows = {row.key: row.value for row in db.query(AppSetting).all()}
    result = []
    for key, meta in MANAGED_SETTINGS.items():
        if key in db_rows:
            effective = _parse(db_rows[key], meta.type)
            source = "database"
        else:
            effective = _effective(meta, settings)
            source = _env_source(meta)

        is_set = effective is not None and effective != meta.default

        if meta.sensitive and is_set:
            display_value: str | None = "***"
        elif effective is None:
            display_value = None
        elif isinstance(effective, bool):
            display_value = "true" if effective else "false"
        else:
            display_value = str(effective)

        result.append(
            {
                "key": key,
                "value": display_value,
                "is_set": is_set,
                "source": source,
                "type": meta.type,
                "description": meta.description,
                "sensitive": meta.sensitive,
                "section": meta.section,
                "env_var": meta.env_var,
            }
        )
    return result


def apply_site_settings(db: DBSession, updates: dict[str, str | None]) -> None:
    """Upsert or delete setting overrides.

    Rules per key:
    - ``None``   → delete the DB override (revert to env/default)
    - ``"***"``  → skip (sentinel meaning "leave sensitive value unchanged")
    - any str   → upsert
    """
    for key, value in updates.items():
        if key not in MANAGED_SETTINGS:
            continue
        if value is None:
            db.execute(delete(AppSetting).where(AppSetting.key == key))
        elif value == "***":
            pass  # sensitive no-change sentinel
        else:
            row = db.get(AppSetting, key)
            now = datetime.now(UTC)
            if row is None:
                db.add(AppSetting(key=key, value=value, updated_at=now))
            else:
                row.value = value
                row.updated_at = now
    db.flush()
    db.commit()
