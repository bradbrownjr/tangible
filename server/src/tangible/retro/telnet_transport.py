"""Telnet RFC 854/857/858 protocol transport layer.

Low-level telnet I/O: IAC handling, echo control, line editing, timeouts.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# Telnet IAC commands per RFC 854
IAC = bytes([255])
WILL = bytes([251])
WONT = bytes([252])
DO = bytes([253])
DONT = bytes([254])
ECHO = bytes([1])
SGA = bytes([3])  # Suppress Go-Ahead

_MAX_LINE = 512
_IDLE_TIMEOUT_SECONDS = 1800  # 30 minutes


class TelnetTransport:
    """Asyncio telnet transport with RFC 854/857/858 compliance."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        idle_timeout: int = _IDLE_TIMEOUT_SECONDS,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.idle_timeout = idle_timeout
        self.echo_on = True

    async def negotiate_echo(self) -> None:
        """Negotiate: WILL SUPPRESS-GO-AHEAD, WILL ECHO."""
        self._write_raw(IAC + WILL + SGA + IAC + WILL + ECHO)
        await self.writer.drain()

    def echo_off(self) -> None:
        """Suppress server-side echo (for password entry)."""
        self.echo_on = False
        self._write_raw(IAC + WONT + ECHO)

    def echo_on_again(self) -> None:
        """Re-enable server-side echo."""
        self.echo_on = True
        self._write_raw(IAC + WILL + ECHO)

    def _write_raw(self, data: bytes) -> None:
        """Write raw bytes (telnet commands)."""
        self.writer.write(data)

    async def write(self, text: str) -> None:
        """Write text and drain."""
        self.writer.write(text.encode("utf-8", errors="replace"))
        await self.writer.drain()

    async def writeln(self, text: str) -> None:
        """Write text with CRLF and drain."""
        await self.write(text + "\r\n")

    async def readline(self) -> str:
        """Read one line, handling telnet IAC, CR+LF/CR+NUL, backspace, timeout.
        
        Returns: stripped UTF-8 line.
        Raises: asyncio.TimeoutError if idle timeout exceeded.
                ConnectionResetError if client disconnects or sends Ctrl+C/Ctrl+D.
        """
        buf = bytearray()
        
        while True:
            try:
                byte = await asyncio.wait_for(
                    self.reader.read(1), timeout=self.idle_timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError("Session idle timeout")
            
            if not byte:
                raise ConnectionResetError("Client disconnected")
            
            b = byte[0]
            
            # Telnet IAC (Interpret As Command) — skip 2 more bytes
            if b == 255:
                cmd = await self.reader.read(1)
                if cmd and cmd[0] in (251, 252, 253, 254):
                    await self.reader.read(1)  # option byte
                continue
            
            # Ctrl+C (SIGINT), Ctrl+D (EOF), Ctrl+Z (SUB)
            if b in (3, 4, 26):
                raise ConnectionResetError("Client cancelled (Ctrl+C/D/Z)")
            
            # Backspace or Delete
            if b in (8, 127):
                if buf:
                    buf.pop()
                    if self.echo_on:
                        self.writer.write(b"\x08 \x08")  # BS SPACE BS for visual delete
                continue
            
            # CR (telnet sends CR+LF or CR+NUL) — end of line
            if b == 13:
                next_byte = await self.reader.read(1)
                # Swallow LF or NUL
                break
            
            # LF alone (some clients)
            if b == 10:
                break
            
            # Regular character
            if len(buf) < _MAX_LINE:
                buf.append(b)
                if self.echo_on:
                    self.writer.write(bytes([b]))
        
        await self.writer.drain()
        return buf.decode("utf-8", errors="replace")

    def close(self) -> None:
        """Close the connection."""
        try:
            self.writer.close()
        except Exception:
            pass
