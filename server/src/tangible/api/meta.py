"""Health, version, and discovery endpoints."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from tangible import __version__
from tangible.config import get_settings
from tangible.db import get_engine, get_session
from tangible.models.user import User
from tangible.services.site_settings import get_site_bool

router = APIRouter(tags=["meta"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe — process is up and answering. Cheap, no I/O."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(response: Response) -> dict[str, str]:
    """Readiness probe — confirms the database is reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except (RuntimeError, SQLAlchemyError) as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "detail": str(exc.__class__.__name__)}
    return {"status": "ready"}


@router.get("/version")
def version() -> dict[str, str]:
    return {"version": __version__}


@router.get("/config/public")
def public_config(db: Session = Depends(get_session)) -> dict[str, object]:
    """Return non-sensitive runtime info for clients (web/mobile)."""
    settings = get_settings()
    providers = []
    if settings.oidc_enabled:
        providers = [
            {
                "name": p.name,
                "label": p.display_name,
                "login_url": f"/auth/oidc/{p.name}/login",
            }
            for p in settings.oidc_providers
        ]
    return {
        "version": __version__,
        "registration_enabled": settings.registration_enabled,
        "setup_required": _no_users_yet(db),
        "oidc_enabled": settings.oidc_enabled,
        "oidc_providers": providers,
        "public_url": settings.public_url,
        "require_2fa": get_site_bool(db, "require_2fa", settings),
    }


def _no_users_yet(db: Session) -> bool:
    """True when the database has zero users (first-run setup state)."""
    try:
        return db.scalar(select(User.id).limit(1)) is None
    except SQLAlchemyError:
        return False


@router.get("/changelog", response_class=PlainTextResponse)
def changelog() -> PlainTextResponse:
    """Serve CHANGELOG.md as plain markdown for the in-app 'What's new' modal."""
    candidates: list[Path] = []
    env_path = os.environ.get("TANGIBLE_CHANGELOG_PATH")
    if env_path:
        candidates.append(Path(env_path))
    here = Path(__file__).resolve()
    candidates.append(here.parents[3] / "CHANGELOG.md")
    candidates.append(Path("/opt/tangible/share/tangible/CHANGELOG.md"))
    candidates.append(Path(sys.prefix) / "share" / "tangible" / "CHANGELOG.md")

    for c in candidates:
        if c.is_file():
            return PlainTextResponse(c.read_text(encoding="utf-8"), media_type="text/markdown")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CHANGELOG not found")
