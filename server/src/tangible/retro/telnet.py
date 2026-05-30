"""Telnet server entry point — delegates to modular session and transport handlers."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from tangible.db import get_engine
from tangible.retro.session import TelnetSession

if TYPE_CHECKING:
    from tangible.config import Settings

log = logging.getLogger(__name__)


async def create_telnet_server(settings: "Settings") -> asyncio.Server:
    """Create and start the telnet server."""
    handler = _make_handler(settings)
    return await asyncio.start_server(
        handler,
        host=settings.telnet_bind,
        port=settings.telnet_port,
    )


def _make_handler(settings: "Settings"):
    """Factory for per-connection telnet handlers."""
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        ip = str(peer[0]) if peer else "unknown"
        
        engine = get_engine()
        session = TelnetSession(reader, writer, ip, settings, engine)
        try:
            await session.run()
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            pass
        except Exception:
            log.exception("Telnet session error from %s", ip)
        finally:
            try:
                writer.close()
            except Exception:
                pass

    return handle
