"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from tangible import __version__
from tangible.api import api_router
from tangible.bootstrap import bootstrap_admin_if_needed, ensure_data_dirs, run_migrations
from tangible.config import Settings, get_settings
from tangible.db import init_engine
from tangible.logging import configure_logging
from tangible.services.metadata import discover_plugins


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    if settings.db_auto_migrate:
        run_migrations(settings)
    bootstrap_admin_if_needed(settings)
    discover_plugins()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)
    ensure_data_dirs(settings)
    init_engine(settings)

    app = FastAPI(
        title="Tangible",
        version=__version__,
        description="Self-hosted personal inventory management",
        lifespan=_lifespan,
    )
    app.state.settings = settings

    # Trusted hosts (from settings)
    if settings.allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[*settings.allowed_hosts, "testserver"],
        )

    # CORS
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Signed-cookie middleware (used for OIDC state, etc.)
    from tangible.security import load_or_create_secret_key

    secret_key = load_or_create_secret_key(settings.secret_key, settings.config_dir)
    app.add_middleware(SessionMiddleware, secret_key=secret_key, https_only=bool(settings.force_https))

    # Hardening (rate limit, security headers, Origin-based CSRF guard)
    from tangible.hardening import install_hardening

    install_hardening(app, settings)

    # Observability (request log + Prometheus /metrics)
    from tangible.observability import install_observability

    install_observability(app, settings)

    # Trust X-Forwarded-* headers when configured to sit behind a reverse proxy.
    if settings.behind_proxy:
        from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    app.include_router(api_router, prefix="/api")

    # MCP server (Model Context Protocol) — mounted at /mcp
    from tangible.api.mcp_server import mcp_app

    app.mount("/mcp", mcp_app(settings))

    _mount_web(app, settings)
    return app


def _mount_web(app: FastAPI, settings: Settings) -> None:
    """Serve the SvelteKit static build as the SPA shell.

    The web dir lookup order:
      1. ``settings.web_dir`` if set and exists
      2. ``<repo>/web/build`` (dev/source layout)
      3. ``/app/web`` (container layout)
    Returns silently if no build is found, leaving the API the only surface.
    """
    from pathlib import Path

    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from starlette.staticfiles import StaticFiles

    candidates = []
    if settings.web_dir:
        candidates.append(Path(settings.web_dir))
    here = Path(__file__).resolve()
    candidates.append(here.parents[3] / "web" / "build")
    candidates.append(Path("/app/web"))

    web_dir: Path | None = next((c for c in candidates if c.is_dir() and (c / "index.html").exists()), None)
    if web_dir is None:
        return

    index_file = web_dir / "index.html"

    # Static assets (hashed) under /_app/*
    if (web_dir / "_app").is_dir():
        app.mount("/_app", StaticFiles(directory=web_dir / "_app"), name="web_app")

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_fallback(full_path: str) -> FileResponse:
        # API routes are all under /api/ so they won't reach here.
        # Block only the few non-API server paths that must not serve the SPA.
        if full_path.startswith(("api/", "openapi.json", "docs", "redoc")):
            raise HTTPException(status_code=404)
        # Try a literal file first (favicon.ico, robots.txt, etc.)
        target = (web_dir / full_path).resolve()
        try:
            target.relative_to(web_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=404) from None
        if target.is_file():
            return FileResponse(target)
        return FileResponse(index_file)


app = create_app()
