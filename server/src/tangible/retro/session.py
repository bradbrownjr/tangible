"""Telnet session manager — orchestrates transport, routing, and workflows."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import sessionmaker

from tangible.retro.command_router import CommandRouter, CommandExit
from tangible.retro.layout import Screen, clear_screen
from tangible.retro.telnet_transport import TelnetTransport

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from tangible.config import Settings

log = logging.getLogger(__name__)

_LOGIN_ATTEMPTS = 3
_IDLE_TIMEOUT_SECONDS = 1800  # 30 minutes


class _BackToMain(Exception):
    """Raised when user requests return to main menu (0 key)."""


class _IdleTimeout(Exception):
    """Raised by transport when session idle timeout exceeded."""


class TelnetSession:
    """Manages a single telnet session: auth, main menu, workflow dispatch."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        ip: str,
        settings: "Settings",
        engine: "Engine",
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.ip = ip
        self.settings = settings
        self.engine = engine
        
        self.transport = TelnetTransport(reader, writer, idle_timeout=_IDLE_TIMEOUT_SECONDS)

        self.username: str | None = None
        self.user_id: str | None = None
        self.default_collection_id: str | None = None

    async def run(self) -> None:
        """Main session entry point."""
        try:
            await self.transport.negotiate_echo()
        except Exception:
            pass

        # Check IP ban status
        Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        with Session() as db:
            from tangible.retro.ban_service import is_banned
            ban = is_banned(db, self.ip, "telnet")
        
        if ban is True:
            await self.transport.writeln("*** ACCESS DENIED — CONTACT ADMINISTRATOR ***")
            return
        if ban is not False:
            wait = max(0, int((ban - datetime.utcnow()).total_seconds()))
            await self.transport.writeln(f"*** ACCESS TEMPORARILY BLOCKED — TRY AGAIN IN {wait} SECONDS ***")
            return

        # Login loop: retry on timeout
        while True:
            authenticated = await self._login()
            if not authenticated:
                return
            
            try:
                await self._main_loop()
                return
            except _IdleTimeout:
                await self.transport.writeln("\r\n\r\n   SESSION TIMED OUT — PLEASE LOG IN AGAIN.")
            except Exception:
                log.exception("Unexpected error in main loop")
                return

    # =========================================================================
    # Authentication
    # =========================================================================

    async def _login(self) -> bool:
        """Authenticate user (3 attempts, enforce ban service rate limiting)."""
        from tangible.models.user import User
        from tangible.retro.auth import authenticate
        from tangible.retro.ban_service import record_attempt
        from sqlalchemy import select

        await self.transport.write(self._login_screen())

        Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

        for attempt in range(_LOGIN_ATTEMPTS):
            try:
                await self.transport.write("\r\n   USER ID  ===> ")
                username = await self.transport.readline()
            except (TimeoutError, ConnectionResetError):
                raise _IdleTimeout()

            if not username:
                continue

            try:
                await self.transport.write("   PASSWORD ===> ")
                self.transport.echo_off()
                password = await self.transport.readline()
                self.transport.echo_on_again()
                await self.transport.write("\r\n")
            except (TimeoutError, ConnectionResetError):
                raise _IdleTimeout()

            with Session() as db:
                from tangible.retro.ban_service import is_banned
                ban = is_banned(db, self.ip, "telnet")
                if ban is True or ban is not False:
                    await self.transport.writeln("*** ACCESS BLOCKED — CONTACT ADMINISTRATOR ***")
                    return False

                user = authenticate(db, username, password)
                if user:
                    record_attempt(db, self.ip, "telnet", success=True)
                    self.username = username
                    self.user_id = user.id
                    return True
                else:
                    ban_result = record_attempt(db, self.ip, "telnet", success=False)
                    remaining = _LOGIN_ATTEMPTS - attempt - 1
                    
                    if ban_result is not None:
                        if ban_result is True:
                            await self.transport.writeln("\r\n   *** TOO MANY FAILURES — ACCESS PERMANENTLY BLOCKED ***")
                        else:
                            wait = max(0, int((ban_result - datetime.utcnow()).total_seconds()))
                            await self.transport.writeln(f"\r\n   *** TOO MANY FAILURES — BLOCKED FOR {wait} SECONDS ***")
                        return False
                    
                    if remaining > 0:
                        await self.transport.writeln(f"\r\n   INVALID LOGIN. {remaining} ATTEMPT(S) REMAINING.")
                    else:
                        await self.transport.writeln("\r\n   TOO MANY INVALID ATTEMPTS. DISCONNECTING.")

        return False

    # =========================================================================
    # Main Menu Loop
    # =========================================================================

    async def _main_loop(self) -> None:
        """Main menu dispatcher — task-area routing."""
        from tangible.models.user import User
        from sqlalchemy import select

        Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        with Session() as db:
            user = db.scalar(select(User).where(User.username == self.username))
            if user and user.default_collection_id:
                self.default_collection_id = user.default_collection_id

        while True:
            try:
                screen = Screen(operator=self.username or "")
                screen.title = "MAIN MENU"
                screen.add_rows([
                    "",
                    "   1  INVENTORY       Lookup / Search / Adjust",
                    "   2  RECEIVING       Add Items / Adjust Stock",
                    "   3  CIRCULATION     Loans / Checkouts / Returns",
                    "   4  SERVICE DESK    Chores / Maintenance",
                    "   5  SHOPPING        Lists / Mark Purchased",
                    "   6  LOCATIONS       Browse / Find Items",
                    "   7  REPORTS         History / Due Tasks",
                    "",
                    "   0  SIGN OFF",
                    "",
                ])
                screen.set_hints("B=BACK  0=SIGN OFF")
                screen.set_prompt("SELECTION ===> ")

                await self.transport.write(clear_screen() + screen.render())
                choice = (await self.transport.readline()).strip().upper()

                if choice == "1":
                    await self._inventory_menu()
                elif choice == "2":
                    await self._receiving_menu()
                elif choice == "3":
                    await self._circulation_menu()
                elif choice == "4":
                    await self._service_desk_menu()
                elif choice == "5":
                    await self._shopping_menu()
                elif choice == "6":
                    await self._locations_menu()
                elif choice == "7":
                    await self._reports_menu()
                elif choice == "0":
                    await self.transport.writeln("\r\n   SIGNING OUT. THANK YOU.\r\n")
                    return
                else:
                    # Ignore invalid, redraw menu
                    pass

            except (TimeoutError, ConnectionResetError):
                raise _IdleTimeout()
            except _BackToMain:
                pass  # Redraw main menu
            except CommandExit as e:
                if e.target == "quit":
                    await self.transport.writeln("\r\n   SIGNING OUT. THANK YOU.\r\n")
                    return
                # else target is "back" or "menu", just redraw

    # =========================================================================
    # Stub Menu Handlers (to be implemented in workflows/)
    # =========================================================================

    async def _inventory_menu(self) -> None:
        """Inventory lookup and search."""
        from tangible.retro.workflows.inventory import inventory_menu
        await inventory_menu(self)

    async def _receiving_menu(self) -> None:
        """Add items to collections."""
        from tangible.retro.workflows.receiving import receiving_menu
        await receiving_menu(self)

    async def _circulation_menu(self) -> None:
        """Loans, checkouts, returns."""
        from tangible.retro.workflows.circulation import circulation_menu
        await circulation_menu(self)

    async def _service_desk_menu(self) -> None:
        """Chores and maintenance."""
        from tangible.retro.workflows.service import service_desk_menu
        await service_desk_menu(self)

    async def _shopping_menu(self) -> None:
        """Shopping lists."""
        from tangible.retro.workflows.shopping import shopping_menu
        await shopping_menu(self)

    async def _locations_menu(self) -> None:
        """Location browsing."""
        from tangible.retro.workflows.locations import locations_menu
        await locations_menu(self)

    async def _reports_menu(self) -> None:
        """Reports and history."""
        from tangible.retro.workflows.reports import reports_menu
        await reports_menu(self)

    # =========================================================================
    # Utilities
    # =========================================================================

    async def _pause(self) -> None:
        """Wait for any key before continuing."""
        try:
            await self.transport.write("\r\n   PRESS ANY KEY TO CONTINUE...")
            await self.transport.readline()
        except (TimeoutError, ConnectionResetError):
            raise _IdleTimeout()

    def _login_screen(self) -> str:
        """Render login screen."""
        return f"""{clear_screen()}
{'='*80}
{'TANGIBLE INVENTORY MANAGEMENT SYSTEM'.center(80)}
{'V0.25.92 — TELNET INTERFACE'.center(80)}
{'='*80}
\r
"""
