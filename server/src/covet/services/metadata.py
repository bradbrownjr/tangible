"""URL metadata scraper + barcode lookup.

Pluggable adapter registry. Each adapter inspects a URL and, if it
matches, fetches and normalises a small dict of suggested item fields.

A separate ``BarcodeAdapter`` registry handles raw UPC/EAN/ISBN lookups
and returns a ranked list of candidates so the client can offer a picker.

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


# ---------------------------------------------------------------------------
# Adapter protocols
# ---------------------------------------------------------------------------


class Adapter(Protocol):
    name: str

    def matches(self, url: str) -> bool: ...

    def fetch(self, url: str, *, client: httpx.Client) -> ScrapeResult: ...


class BarcodeAdapter(Protocol):
    name: str

    def lookup(self, barcode: str, *, client: httpx.Client) -> list[ScrapeResult]: ...


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
# Barcode adapters
# ---------------------------------------------------------------------------


class OpenLibraryBarcodeAdapter:
    name = "openlibrary"

    def lookup(self, barcode: str, *, client: httpx.Client) -> list[ScrapeResult]:
        isbn = re.sub(r"[^0-9Xx]", "", barcode)
        if len(isbn) not in (10, 13):
            return []
        api = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        resp = client.get(api, follow_redirects=True)
        if resp.status_code != 200:
            return []
        data = resp.json().get(f"ISBN:{isbn}") or {}
        if not data:
            return []
        title = data.get("title")
        if not title:
            return []
        authors = ", ".join(a.get("name", "") for a in data.get("authors", []))
        cover = (data.get("cover") or {}).get("medium")
        attrs: dict[str, Any] = {"isbn": isbn}
        if authors:
            attrs["creator"] = authors
        if data.get("number_of_pages"):
            attrs["pages"] = data["number_of_pages"]
        if data.get("publish_date"):
            attrs["published"] = data["publish_date"]
        return [ScrapeResult(
            provider=self.name,
            url=f"https://openlibrary.org/isbn/{isbn}",
            title=title,
            description=authors or None,
            image_url=cover,
            item_type="book",
            category="books.print",
            attrs=attrs,
        )]


class MusicBrainzBarcodeAdapter:
    name = "musicbrainz"

    def lookup(self, barcode: str, *, client: httpx.Client) -> list[ScrapeResult]:
        code = re.sub(r"\D", "", barcode)
        if len(code) < 8:
            return []
        settings = get_settings()
        ua = settings.musicbrainz_user_agent or USER_AGENT
        resp = client.get(
            f"https://musicbrainz.org/ws/2/release?barcode={code}&fmt=json&limit=5",
            headers={"User-Agent": ua},
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []
        releases = resp.json().get("releases") or []
        results = []
        for r in releases[:5]:
            title = r.get("title")
            if not title:
                continue
            artist = "".join(
                (c.get("name") or c.get("artist", {}).get("name", "")) + c.get("joinphrase", "")
                for c in (r.get("artist-credit") or [])
                if isinstance(c, dict)
            ).strip()
            attrs: dict[str, Any] = {"barcode": code}
            if r.get("date"):
                attrs["published"] = r["date"]
            if r.get("id"):
                attrs["musicbrainz_id"] = r["id"]
            results.append(ScrapeResult(
                provider=self.name,
                url=f"https://musicbrainz.org/release/{r.get('id', '')}",
                title=title,
                description=artist or None,
                item_type="music",
                category="music.cd",
                attrs=attrs,
            ))
        return results


class OpenFoodFactsBarcodeAdapter:
    name = "openfoodfacts"

    def lookup(self, barcode: str, *, client: httpx.Client) -> list[ScrapeResult]:
        code = re.sub(r"\D", "", barcode)
        if len(code) < 8:
            return []
        resp = client.get(
            f"https://world.openfoodfacts.org/api/v2/product/{code}.json",
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        if data.get("status") != 1:
            return []
        product = data.get("product") or {}
        title = product.get("product_name") or product.get("product_name_en")
        if not title:
            return []
        brand = product.get("brands", "")
        image = product.get("image_front_url") or product.get("image_url")
        attrs: dict[str, Any] = {"barcode": code}
        if brand:
            attrs["creator"] = brand
        if product.get("quantity"):
            attrs["quantity_label"] = product["quantity"]
        return [ScrapeResult(
            provider=self.name,
            url=f"https://world.openfoodfacts.org/product/{code}",
            title=title,
            description=brand or None,
            image_url=image,
            attrs=attrs,
        )]


class GoogleBooksAdapter:
    name = "google_books"

    def lookup(self, barcode: str, *, client: httpx.Client) -> list[ScrapeResult]:
        isbn = re.sub(r"[^0-9Xx]", "", barcode)
        if len(isbn) not in (10, 13):
            return []
        settings = get_settings()
        params: dict[str, str] = {"q": f"isbn:{isbn}", "maxResults": "5"}
        if settings.google_books_api_key:
            params["key"] = settings.google_books_api_key
        resp = client.get("https://www.googleapis.com/books/v1/volumes", params=params)
        if resp.status_code != 200:
            return []
        results = []
        for item in (resp.json().get("items") or [])[:5]:
            info = item.get("volumeInfo") or {}
            title = info.get("title")
            if not title:
                continue
            authors = ", ".join(info.get("authors") or [])
            description = (info.get("description") or "")[:200] or None
            image = (info.get("imageLinks") or {}).get("thumbnail")
            if image:
                image = image.replace("http://", "https://")
            attrs: dict[str, Any] = {"isbn": isbn}
            if authors:
                attrs["creator"] = authors
            if info.get("publishedDate"):
                attrs["published"] = info["publishedDate"]
            if info.get("pageCount"):
                attrs["pages"] = info["pageCount"]
            results.append(ScrapeResult(
                provider=self.name,
                url=f"https://books.google.com/books?isbn={isbn}",
                title=title,
                description=description or authors or None,
                image_url=image,
                item_type="book",
                category="books.print",
                attrs=attrs,
            ))
        return results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ADAPTERS: list[Adapter] = [OpenLibraryAdapter(), OpenGraphAdapter()]
_BARCODE_ADAPTERS: list[BarcodeAdapter] = [
    OpenLibraryBarcodeAdapter(),
    MusicBrainzBarcodeAdapter(),
    OpenFoodFactsBarcodeAdapter(),
    GoogleBooksAdapter(),
]


def register_adapter(adapter: Adapter) -> None:
    # Prepend so custom adapters win over OpenGraph fallback.
    _ADAPTERS.insert(0, adapter)


def barcode_lookup(barcode: str, *, client: httpx.Client | None = None) -> list[ScrapeResult]:
    """Query all enabled barcode adapters and return a deduplicated candidate list."""
    own = client is None
    if client is None:
        client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    seen_titles: set[str] = set()
    results: list[ScrapeResult] = []
    try:
        for adapter in _BARCODE_ADAPTERS:
            try:
                for r in adapter.lookup(barcode, client=client):
                    key = (r.provider, (r.title or "").lower())
                    if key not in seen_titles:
                        seen_titles.add(key)
                        results.append(r)
            except Exception:
                continue
    finally:
        if own:
            client.close()
    return results


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
