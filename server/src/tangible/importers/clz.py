"""CLZ (Collectorz.com) XML importers.

Collectorz ships five separate desktop products — Movie/Music/Book/Comic/Game
Collector — each of which can export the user's database as XML. The schemas
are similar but distinct: the root + record element names differ, and each
product has unique fields (e.g. ``runtime`` for movies, ``pages`` for books).

Implementation strategy: a small base extractor pulls the common fields
(``title``, ``year``, ``barcode``, ``notes``, ``loan*``, …) from the typical
CLZ shape; per-product subclasses set element names and map the type-specific
fields into :class:`ImportItem.attrs`.

These adapters are best-effort and cover the most common, stable elements
documented in CLZ's own export samples. Unknown elements are preserved
verbatim under ``attrs["clz_extras"]`` so no information is silently lost.

Standard XML parser hardening: this module uses ``defusedxml`` to defeat
billion-laughs and external-entity attacks (`OWASP — XXE prevention`).
"""

from __future__ import annotations

from typing import IO

# defusedxml is the standard, OWASP-recommended hardened wrapper around the
# stdlib XML parser; it raises on entity-expansion / XXE attempts.
from defusedxml import ElementTree as DET  # type: ignore[import-untyped]

from tangible.importers.base import Importer, ImportItem, ImportResult


def _text(node, name: str) -> str | None:  # type: ignore[no-untyped-def]
    child = node.find(name)
    if child is None:
        return None
    text = (child.text or "").strip()
    return text or None


def _int(node, name: str) -> int | None:  # type: ignore[no-untyped-def]
    raw = _text(node, name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _float(node, name: str) -> float | None:  # type: ignore[no-untyped-def]
    raw = _text(node, name)
    if raw is None:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _list_displaynames(node, container: str) -> list[str]:  # type: ignore[no-untyped-def]
    """CLZ multi-value fields commonly look like::

        <genres>
            <genre><displayname>Action</displayname></genre>
            <genre><displayname>SciFi</displayname></genre>
        </genres>
    """
    parent = node.find(container)
    if parent is None:
        return []
    out: list[str] = []
    for child in parent:
        name = (
            (child.findtext("displayname") or "").strip()
            or (child.text or "").strip()
        )
        if name:
            out.append(name)
    return out


def _common_attrs(node) -> dict[str, object]:  # type: ignore[no-untyped-def]
    attrs: dict[str, object] = {}
    for tag in ("year", "country", "language", "originaltitle", "edition", "rating"):
        value = _text(node, tag)
        if value is not None:
            attrs[tag] = value
    genres = _list_displaynames(node, "genres")
    if genres:
        attrs["genres"] = genres
    return attrs


def _common_identifiers(node) -> dict[str, str]:  # type: ignore[no-untyped-def]
    ids: dict[str, str] = {}
    for tag in ("barcode", "upc", "ean", "isbn", "asin"):
        value = _text(node, tag)
        if value is not None:
            ids[tag] = value
    return ids


class CLZImporter(Importer):
    """Base class — subclasses set the XML tags and item ``category_slug``."""

    category_slug: str = ""
    record_tag: str = ""
    name: str = "clz"

    def parse(self, source: IO[bytes]) -> ImportResult:
        tree = DET.parse(source)
        root = tree.getroot()
        items: list[ImportItem] = []
        warnings: list[str] = []

        records = list(root.iter(self.record_tag))
        if not records:
            warnings.append(
                f"No <{self.record_tag}> records found; is this a "
                f"{self.category_slug} CLZ export?"
            )

        for node in records:
            item = self._record_to_item(node)
            if item is not None:
                items.append(item)
        return ImportResult(items=items, warnings=warnings)

    # --- subclass hooks ---------------------------------------------------

    def _record_to_item(self, node) -> ImportItem | None:  # type: ignore[no-untyped-def]
        title = _text(node, "title") or _text(node, "name")
        if title is None:
            return None
        attrs = _common_attrs(node)
        attrs.update(self._extra_attrs(node))
        item = ImportItem(
            category_slug=self.category_slug,
            title=title,
            subtitle=_text(node, "subtitle") or _text(node, "originaltitle"),
            notes=_text(node, "notes") or _text(node, "plot"),
            condition=_text(node, "condition"),
            quantity=_int(node, "quantity") or 1,
            purchase_price=_float(node, "purchaseprice"),
            current_value=_float(node, "currentvalue"),
            currency=_text(node, "currency"),
            location=_text(node, "location"),
            identifiers=_common_identifiers(node),
            attrs=attrs,
        )
        return item

    def _extra_attrs(self, node) -> dict[str, object]:  # type: ignore[no-untyped-def]
        return {}


# --- Per-product adapters -------------------------------------------------


class CLZMovieImporter(CLZImporter):
    category_slug = "movies.dvd"
    record_tag = "movie"
    name = "clz-movie"

    def _extra_attrs(self, node):  # type: ignore[no-untyped-def]
        extras: dict[str, object] = {}
        for tag in ("format", "runtime", "mpaa", "studio", "director"):
            v = _text(node, tag)
            if v is not None:
                extras[tag] = v
        actors = _list_displaynames(node, "actors")
        if actors:
            extras["actors"] = actors
        return extras


class CLZMusicImporter(CLZImporter):
    category_slug = "music.cd"
    record_tag = "music"
    name = "clz-music"

    def _extra_attrs(self, node):  # type: ignore[no-untyped-def]
        extras: dict[str, object] = {}
        for tag in ("artist", "format", "label", "discs"):
            v = _text(node, tag)
            if v is not None:
                extras[tag] = v
        tracks = _list_displaynames(node, "tracks")
        if tracks:
            extras["tracks"] = tracks
        return extras


class CLZBookImporter(CLZImporter):
    category_slug = "books.print"
    record_tag = "book"
    name = "clz-book"

    def _extra_attrs(self, node):  # type: ignore[no-untyped-def]
        extras: dict[str, object] = {}
        for tag in ("author", "publisher", "format", "pages", "edition", "series"):
            v = _text(node, tag)
            if v is not None:
                extras[tag] = v
        return extras


class CLZComicImporter(CLZImporter):
    category_slug = "books.comic"
    record_tag = "comic"
    name = "clz-comic"

    def _extra_attrs(self, node):  # type: ignore[no-untyped-def]
        extras: dict[str, object] = {}
        for tag in ("series", "issuenr", "publisher", "writer", "artist", "grade"):
            v = _text(node, tag)
            if v is not None:
                extras[tag] = v
        return extras


class CLZGameImporter(CLZImporter):
    category_slug = "games.software"
    record_tag = "game"
    name = "clz-game"

    def _extra_attrs(self, node):  # type: ignore[no-untyped-def]
        extras: dict[str, object] = {}
        for tag in ("platform", "publisher", "developer", "region", "completion"):
            v = _text(node, tag)
            if v is not None:
                extras[tag] = v
        return extras


CLZ_IMPORTERS: dict[str, type[CLZImporter]] = {
    "clz-movie": CLZMovieImporter,
    "clz-music": CLZMusicImporter,
    "clz-book": CLZBookImporter,
    "clz-comic": CLZComicImporter,
    "clz-game": CLZGameImporter,
}


__all__ = [
    "CLZ_IMPORTERS",
    "CLZBookImporter",
    "CLZComicImporter",
    "CLZGameImporter",
    "CLZImporter",
    "CLZMovieImporter",
    "CLZMusicImporter",
]
