"""Curated community scraper registry.

This registry is intentionally version-controlled in the repo so users can
import trusted presets with one click and contribute improvements via PRs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryEntry:
    id: str
    name: str
    provider: str
    description: str
    category_slug: str
    homepage: str
    fields: list[dict]
    trusted: bool = True


_ENTRIES: list[RegistryEntry] = [
    RegistryEntry(
        id="openlibrary-books",
        name="Open Library Books",
        provider="openlibrary",
        description="Book metadata preset aligned to Open Library ISBN lookups.",
        category_slug="books.print",
        homepage="https://openlibrary.org/",
        fields=[
            {"key": "isbn", "label": "ISBN", "type": "text", "required": True},
            {"key": "creator", "label": "Author(s)", "type": "text"},
            {"key": "published", "label": "Published", "type": "text"},
            {"key": "pages", "label": "Pages", "type": "number"},
        ],
    ),
    RegistryEntry(
        id="musicbrainz-releases",
        name="MusicBrainz Releases",
        provider="musicbrainz",
        description="Music release preset aligned to MusicBrainz barcode matches.",
        category_slug="music.cd",
        homepage="https://musicbrainz.org/",
        fields=[
            {"key": "barcode", "label": "Barcode", "type": "text", "required": True},
            {"key": "musicbrainz_id", "label": "MusicBrainz ID", "type": "text"},
            {"key": "published", "label": "Release date", "type": "text"},
            {"key": "creator", "label": "Artist", "type": "text"},
        ],
    ),
    RegistryEntry(
        id="openfoodfacts-pantry",
        name="Open Food Facts Pantry",
        provider="openfoodfacts",
        description="Consumable pantry preset aligned to Open Food Facts lookups.",
        category_slug="spices.pantry_item",
        homepage="https://world.openfoodfacts.org/",
        fields=[
            {"key": "barcode", "label": "Barcode", "type": "text", "required": True},
            {"key": "creator", "label": "Brand", "type": "text"},
            {"key": "quantity_label", "label": "Pack size", "type": "text"},
            {"key": "use_by", "label": "Use by", "type": "date"},
        ],
    ),
]


def list_entries() -> list[RegistryEntry]:
    return list(_ENTRIES)


def get_entry(entry_id: str) -> RegistryEntry | None:
    for entry in _ENTRIES:
        if entry.id == entry_id:
            return entry
    return None
