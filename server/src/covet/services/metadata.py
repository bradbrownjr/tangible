"""URL metadata scraper.

Pluggable adapter registry. Each adapter inspects a URL and, if it
matches, fetches and normalises a small dict of suggested item fields.

The default ``OpenGraphAdapter`` handles any URL by parsing OpenGraph /
``<title>`` / ``<meta name="description">`` tags. Source-specific
adapters (Discogs, Open Library, IGDB, ...) can be added by registering
with :func:`register_adapter`.

SSRF protection: only public IPs reachable over http/https are allowed.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from covet.config import get_settings

USER_AGENT = "Covet/1.0 (+https://github.com/bradbrownjr/covet)"
TIMEOUT = httpx.Timeout(8.0)
MAX_BYTES = 1_000_000


class ScrapeError(RuntimeError):
    """Raised when a URL cannot be scraped."""


@dataclass
class ScrapeResult:
    provider: str
    url: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    item_type: str | None = None
    category: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


class Adapter(Protocol):
    name: str

    def matches(self, url: str) -> bool: ...

    def fetch(self, url: str, *, client: httpx.Client) -> ScrapeResult: ...


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------


def _is_public_host(host: str) -> bool:
    settings = get_settings()
    # Allow loopback only when explicitly listed (e.g. local dev).
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            if host in getattr(settings, "scraper_allowed_hosts", []) or []:
                continue
            return False
    return True


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScrapeError("URL must be http or https")
    if not parsed.hostname:
        raise ScrapeError("URL is missing a host")
    if not _is_public_host(parsed.hostname):
        raise ScrapeError("URL host is not publicly reachable")
    return url


# ---------------------------------------------------------------------------
# OpenGraph / generic HTML adapter
# ---------------------------------------------------------------------------


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.og: dict[str, str] = {}
        self.meta: dict[str, str] = {}
        self._in_title = False
        self._title_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): v or "" for k, v in attrs}
        if tag == "title":
            self._in_title = True
            self._title_buf = []
        elif tag == "meta":
            content = a.get("content")
            if not content:
                return
            prop = a.get("property", "").lower()
            name = a.get("name", "").lower()
            if prop.startswith("og:"):
                self.og[prop[3:]] = content
            if name in ("description", "twitter:description"):
                self.meta["description"] = content
            if name in ("title", "twitter:title"):
                self.meta.setdefault("title", content)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            joined = "".join(self._title_buf).strip()
            if joined:
                self.title = joined

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_buf.append(data)


class OpenGraphAdapter:
    name = "opengraph"

    def matches(self, url: str) -> bool:
        return True  # last-resort

    def fetch(self, url: str, *, client: httpx.Client) -> ScrapeResult:
        with client.stream("GET", url, follow_redirects=True) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype.lower():
                raise ScrapeError(f"unsupported content-type: {ctype}")
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes():
                chunks.append(chunk)
                total += len(chunk)
                if total >= MAX_BYTES:
                    break
            body = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
        parser = _MetaParser()
        parser.feed(body)
        title = parser.og.get("title") or parser.meta.get("title") or parser.title
        desc = parser.og.get("description") or parser.meta.get("description")
        img = parser.og.get("image")
        return ScrapeResult(
            provider=self.name,
            url=url,
            title=_clean(title),
            description=_clean(desc),
            image_url=img,
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


# ---------------------------------------------------------------------------
# Open Library (books) — works for openlibrary.org/isbn/{isbn} URLs
# ---------------------------------------------------------------------------


class OpenLibraryAdapter:
    name = "openlibrary"
    _isbn_re = re.compile(r"openlibrary\.org/isbn/([0-9Xx\-]{10,17})")

    def matches(self, url: str) -> bool:
        return bool(self._isbn_re.search(url))

    def fetch(self, url: str, *, client: httpx.Client) -> ScrapeResult:
        m = self._isbn_re.search(url)
        if not m:
            raise ScrapeError("not an Open Library ISBN URL")
        isbn = m.group(1).replace("-", "")
        api = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        resp = client.get(api, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json().get(f"ISBN:{isbn}") or {}
        if not data:
            raise ScrapeError("no Open Library record")
        title = data.get("title")
        authors = ", ".join(a.get("name", "") for a in data.get("authors", []))
        cover = (data.get("cover") or {}).get("medium")
        attrs: dict[str, Any] = {"isbn": isbn}
        if authors:
            attrs["authors"] = authors
        if data.get("number_of_pages"):
            attrs["pages"] = data["number_of_pages"]
        if data.get("publish_date"):
            attrs["published"] = data["publish_date"]
        return ScrapeResult(
            provider=self.name,
            url=url,
            title=title,
            description=authors or None,
            image_url=cover,
            item_type="book",
            category="books.print",
            attrs=attrs,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ADAPTERS: list[Adapter] = [OpenLibraryAdapter(), OpenGraphAdapter()]


def register_adapter(adapter: Adapter) -> None:
    # Prepend so custom adapters win over OpenGraph fallback.
    _ADAPTERS.insert(0, adapter)


def scrape(url: str, *, client: httpx.Client | None = None) -> ScrapeResult:
    validate_url(url)
    own = client is None
    if client is None:
        client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    try:
        for adapter in _ADAPTERS:
            if adapter.matches(url):
                try:
                    return adapter.fetch(url, client=client)
                except ScrapeError:
                    continue
                except httpx.HTTPError as exc:
                    raise ScrapeError(str(exc)) from exc
        raise ScrapeError("no adapter matched")
    finally:
        if own:
            client.close()
