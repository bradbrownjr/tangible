"""Startup helpers (data dirs, migrations, admin bootstrap)."""

from __future__ import annotations

import os
from pathlib import Path

import structlog
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from tangible.auth.service import create_user
from tangible.config import Settings
from tangible.db import get_engine, init_engine

log = structlog.get_logger(__name__)


def ensure_data_dirs(settings: Settings) -> None:
    for path in (settings.data_dir, settings.config_dir, settings.photos_dir):
        if path is not None:
            Path(path).mkdir(parents=True, exist_ok=True)


def _find_alembic_dir() -> Path:
    """Locate the ``alembic`` migrations directory.

    Search order:
      1. ``$TANGIBLE_ALEMBIC_DIR`` (explicit override, used by Docker image).
      2. Repo layout (``server/alembic`` next to ``server/src``) — for dev.
      3. ``<sys.prefix>/share/tangible/alembic`` — installed/Docker fallback.
    """
    import sys

    env_override = os.environ.get("TANGIBLE_ALEMBIC_DIR")
    if env_override:
        return Path(env_override)

    server_root = Path(__file__).resolve().parent.parent.parent
    candidate = server_root / "alembic"
    if candidate.is_dir():
        return candidate

    return Path(sys.prefix) / "share" / "tangible" / "alembic"


def _alembic_config(settings: Settings) -> Config:
    alembic_dir = _find_alembic_dir()
    ini_path = alembic_dir.parent / "alembic.ini"
    cfg = Config(str(ini_path)) if ini_path.is_file() else Config()
    cfg.set_main_option("script_location", str(alembic_dir))
    cfg.set_main_option("sqlalchemy.url", settings.resolved_database_url())
    return cfg


def run_migrations(settings: Settings) -> None:
    """Run Alembic upgrade head."""
    log.info("running_migrations", url=settings.resolved_database_url().split("@")[-1])
    cfg = _alembic_config(settings)
    command.upgrade(cfg, "head")


def bootstrap_admin_if_needed(settings: Settings) -> None:
    """Create the initial admin from env if no users exist."""
    from sqlalchemy.orm import Session as DBSession

    from tangible.models import User

    if not (settings.admin_username and settings.admin_password):
        return

    try:
        engine = get_engine()
    except RuntimeError:
        engine = init_engine(settings)

    with DBSession(engine) as db:
        existing = db.scalar(select(User).limit(1))
        if existing is not None:
            return
        log.info("bootstrapping_admin", username=settings.admin_username)
        create_user(
            db,
            username=settings.admin_username,
            password=settings.admin_password,
            email=settings.admin_email,
            is_admin=True,
        )
        db.commit()
