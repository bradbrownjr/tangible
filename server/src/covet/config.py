"""Application configuration via pydantic-settings.

Environment variables are prefixed ``COVET_`` and may also be loaded from
``${COVET_CONFIG_DIR}/covet.env`` or ``covet.yaml``. Secrets accept a
``<NAME>_FILE`` companion variable that points at a file whose contents
become the value (Docker secrets / Unraid pattern).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _read_secret_file(env_name: str) -> str | None:
    """Return file contents if ``<env_name>_FILE`` is set and readable."""
    file_var = f"{env_name}_FILE"
    path = os.environ.get(file_var)
    if not path:
        return None
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _load_yaml_overlay() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (flat-overlay, oidc_providers).

    Top-level scalars become ``COVET_*`` env-style keys. The optional
    ``oidc_providers:`` list is returned separately because nested config
    can't round-trip cleanly through env vars.
    """
    config_dir = os.environ.get("COVET_CONFIG_DIR", "/config")
    yaml_path = Path(config_dir) / "covet.yaml"
    if not yaml_path.is_file():
        return {}, []
    try:
        loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}, []
    if not isinstance(loaded, dict):
        return {}, []
    providers_raw = loaded.pop("oidc_providers", None)
    providers: list[dict[str, Any]] = []
    if isinstance(providers_raw, list):
        providers = [p for p in providers_raw if isinstance(p, dict)]
    flat: dict[str, Any] = {}
    for k, v in loaded.items():
        if isinstance(v, list | dict):
            continue  # only scalars supported via env-style overlay
        flat[f"COVET_{k.upper()}" if not k.upper().startswith("COVET_") else k.upper()] = v
    return flat, providers


class OIDCProvider(BaseModel):
    """Configuration for a single OIDC provider."""

    name: str
    display_name: str
    issuer: str
    client_id: str
    client_secret: str
    scopes: str = "openid profile email"
    redirect_uri: str | None = None
    admin_groups: list[str] = Field(default_factory=list)
    username_claim: str = "preferred_username"


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_prefix="COVET_",
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    # Core / runtime
    data_dir: Path = Path("/data")
    config_dir: Path = Path("/config")
    web_dir: Path | None = None
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    log_format: str = "console"
    tz: str = "UTC"

    # Database
    database_url: str | None = None
    db_type: str = "sqlite"
    db_host: str | None = None
    db_port: int | None = None
    db_name: str = "covet"
    db_user: str | None = None
    db_password: str | None = None
    db_sslmode: str | None = None
    db_pool_size: int = 5
    db_pool_max_overflow: int = 10
    db_auto_migrate: bool = True

    # Reverse proxy / public URL
    public_url: str = "http://localhost:8000"
    behind_proxy: bool = False
    trusted_proxies: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "127.0.0.1/32",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ]
    )
    force_https: bool | None = None
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    allowed_hosts: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # Sessions / auth
    secret_key: str | None = None
    session_cookie_name: str = "covet_session"
    session_cookie_secure: bool | None = None
    session_cookie_samesite: str = "lax"
    session_ttl_hours: int = 720
    registration_enabled: bool = True
    password_min_length: int = 12

    # OIDC
    oidc_enabled: bool = False
    oidc_auto_create_users: bool = True
    oidc_default_role: str = "viewer"
    oidc_providers: list[OIDCProvider] = Field(default_factory=list)

    # Photo storage
    photos_dir: Path | None = None
    photos_max_bytes: int = 25 * 1024 * 1024
    photos_thumbnail_sizes: Annotated[list[int], NoDecode] = Field(
        default_factory=lambda: [256, 1024]
    )

    # Document attachment storage
    documents_dir: Path | None = None
    documents_max_bytes: int = 50 * 1024 * 1024

    # Sync
    sync_snapshot_interval: int = 100
    sync_retention_days: int = 30
    sync_max_batch: int = 500

    # Rate limiting
    rate_limit_login: str = "5/minute"
    rate_limit_api: str = "120/minute"
    api_token_ttl_days: int = 0

    # Observability
    request_log_enabled: bool = True
    metrics_enabled: bool = True

    # SMTP (optional)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True

    # First-run admin bootstrap
    admin_username: str | None = None
    admin_password: str | None = None
    admin_email: str | None = None

    # Integration API keys
    discogs_token: str | None = None
    tmdb_api_key: str | None = None
    igdb_client_id: str | None = None
    igdb_client_secret: str | None = None
    musicbrainz_user_agent: str | None = None
    upcitemdb_key: str | None = None
    google_books_api_key: str | None = None

    # ---- validators / derived values -------------------------------------------------

    @field_validator("trusted_proxies", "cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def _split_csv(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("photos_thumbnail_sizes", mode="before")
    @classmethod
    def _split_int_csv(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _resolve_secrets(self) -> Settings:
        # Pull <NAME>_FILE secrets for selected fields.
        secret_fields = {
            "db_password": "COVET_DB_PASSWORD",
            "secret_key": "COVET_SECRET_KEY",
            "smtp_password": "COVET_SMTP_PASSWORD",
            "admin_password": "COVET_ADMIN_PASSWORD",
            "discogs_token": "COVET_DISCOGS_TOKEN",
            "tmdb_api_key": "COVET_TMDB_API_KEY",
            "igdb_client_secret": "COVET_IGDB_CLIENT_SECRET",
            "upcitemdb_key": "COVET_UPCITEMDB_KEY",
            "google_books_api_key": "COVET_GOOGLE_BOOKS_API_KEY",
        }
        for attr, env_name in secret_fields.items():
            if getattr(self, attr) is None:
                value = _read_secret_file(env_name)
                if value is not None:
                    object.__setattr__(self, attr, value)
        return self

    @model_validator(mode="after")
    def _derive_defaults(self) -> Settings:
        if self.photos_dir is None:
            object.__setattr__(self, "photos_dir", self.data_dir / "photos")
        if self.documents_dir is None:
            object.__setattr__(self, "documents_dir", self.data_dir / "documents")

        parsed = urlparse(self.public_url)
        is_https = parsed.scheme == "https"

        if self.force_https is None:
            object.__setattr__(self, "force_https", is_https)

        if self.session_cookie_secure is None:
            object.__setattr__(self, "session_cookie_secure", is_https)

        if not self.cors_origins:
            origins = [self.public_url.rstrip("/")]
            if "localhost" not in origins[0]:
                origins.append("http://localhost:5173")
            object.__setattr__(self, "cors_origins", origins)

        if not self.allowed_hosts:
            host = parsed.hostname
            # Always trust loopback names so the container HEALTHCHECK and
            # local probes (curl 127.0.0.1) succeed regardless of public_url.
            hosts: list[str] = ["localhost", "127.0.0.1", "::1"]
            if host and host not in hosts:
                hosts.insert(0, host)
            object.__setattr__(self, "allowed_hosts", hosts)

        if self.musicbrainz_user_agent is None:
            object.__setattr__(
                self,
                "musicbrainz_user_agent",
                f"Covet/{__import__('covet').__version__} (+{self.public_url})",
            )

        return self

    def resolved_database_url(self) -> str:
        """Return a SQLAlchemy URL, assembling from discrete fields if needed."""
        if self.database_url:
            return self.database_url

        if self.db_type == "sqlite":
            return f"sqlite:///{self.data_dir / 'covet.db'}"

        driver_map = {
            "postgresql": "postgresql+psycopg",
            "mysql": "mysql+pymysql",
            "mariadb": "mysql+pymysql",
        }
        driver = driver_map.get(self.db_type)
        if driver is None:
            raise ValueError(f"Unsupported COVET_DB_TYPE: {self.db_type}")

        if not self.db_host:
            raise ValueError("COVET_DB_HOST is required when COVET_DATABASE_URL is unset")

        port = self.db_port or {"postgresql": 5432, "mysql": 3306, "mariadb": 3306}[self.db_type]
        user_part = ""
        if self.db_user:
            user_part = self.db_user
            if self.db_password:
                user_part = f"{self.db_user}:{self.db_password}"
            user_part += "@"

        url = f"{driver}://{user_part}{self.db_host}:{port}/{self.db_name}"
        if self.db_sslmode:
            sep = "?"
            url = f"{url}{sep}sslmode={self.db_sslmode}"
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached :class:`Settings`; YAML overlay is applied as defaults."""
    overlay, providers = _load_yaml_overlay()
    # YAML overlay only fills variables NOT already in env, so env always wins.
    for key, value in overlay.items():
        os.environ.setdefault(key, str(value))
    settings = Settings()
    if providers and not settings.oidc_providers:
        object.__setattr__(
            settings, "oidc_providers", [OIDCProvider(**p) for p in providers]
        )
    return settings


def reset_settings_cache() -> None:
    """Clear the cached settings (used in tests)."""
    get_settings.cache_clear()
