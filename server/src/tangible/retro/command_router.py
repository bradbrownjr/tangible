"""Command parsing and routing for telnet shell.

Supports both numeric menu selection and terse operator commands.
Routes to appropriate handler functions based on context.
"""

from __future__ import annotations

import logging
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from tangible.retro.session import TelnetSession

log = logging.getLogger(__name__)


class CommandRouter:
    """Route numeric and text commands to handlers."""

    def __init__(self):
        # Routes: dict mapping command string to handler function
        self.routes: dict[str, Callable] = {}
        
        # Context-sensitive command aliases (e.g., "ITEM" -> "I" in inventory context)
        self.aliases: dict[str, str] = {}
        
        # Commands that apply globally (MENU, BACK, QUIT, HELP)
        self.global_commands = {"MENU": self._handle_menu, "BACK": self._handle_back, "QUIT": self._handle_quit, "HELP": self._handle_help, "0": self._handle_main_menu}

    def register(self, command: str, handler: Callable) -> None:
        """Register a command handler.
        
        command: numeric string (e.g., "1", "7") or mnemonic (e.g., "ITEM", "ADJ", "LOAN")
        handler: async function(session: TelnetSession, *args: str) -> None
        """
        self.routes[command.upper()] = handler

    def register_alias(self, alias: str, canonical: str) -> None:
        """Register a command alias (e.g., "I" -> "ITEM")."""
        self.aliases[alias.upper()] = canonical.upper()

    async def route(self, session: TelnetSession, command: str) -> bool:
        """Route a command to its handler.
        
        Returns: True if command was handled, False if unrecognized.
        Raises: CommandExit for menu/back/quit operations.
        """
        cmd = command.strip().upper()
        
        if not cmd:
            return False
        
        # Resolve aliases
        if cmd in self.aliases:
            cmd = self.aliases[cmd]
        
        # Try global commands first
        if cmd in self.global_commands:
            await self.global_commands[cmd](session)
            return True
        
        # Try registered routes
        if cmd in self.routes:
            handler = self.routes[cmd]
            await handler(session)
            return True
        
        return False

    async def _handle_menu(self, session: TelnetSession) -> None:
        """Return to main menu."""
        raise CommandExit("menu")

    async def _handle_back(self, session: TelnetSession) -> None:
        """Go back (exit current screen)."""
        raise CommandExit("back")

    async def _handle_quit(self, session: TelnetSession) -> None:
        """Quit/sign off."""
        raise CommandExit("quit")

    async def _handle_main_menu(self, session: TelnetSession) -> None:
        """Shorthand for MENU (0 = main menu)."""
        raise CommandExit("menu")

    async def _handle_help(self, session: "TelnetSession") -> None:
        """Show help (TBD)."""
        pass


class CommandExit(Exception):
    """Raised to exit a screen/menu (handled by session loop)."""

    def __init__(self, target: str = "back"):
        self.target = target  # "back", "menu", "quit"
        super().__init__(f"Exit to {target}")


class CommandContext:
    """Track current operational context for command routing."""

    def __init__(self, mode: str = "main"):
        self.mode = mode  # "main", "inventory", "circulation", "service", etc.
        self.current_item_id: str | None = None
        self.current_collection_id: str | None = None
        self.last_search_term: str | None = None
        self.last_search_results: list = []
