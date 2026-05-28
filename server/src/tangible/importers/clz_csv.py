"""CLZ (Collectorz.com) CSV importers.

Collectorz apps can export the user's library as a CSV in addition to the
standard XML format.  The CSV layout is the same regardless of which desktop
or mobile product generated it; the only differences are which platform-
specific columns appear and the value in the "Platform" / "Type" column.

One pre-built :class:`CSVImporter` subclass is provided per CLZ product
(Games, Movies, Music, Books, Comics).  Each subclass hard-codes the full
column mapping so users do not have to specify it manually.

Columns that carry no collector-relevant data (Added Date, Sort Title,
Purchase Year, Added Year, Modified Date, Owner, Due Date, Loan Date,
Loaned To, Completed Year, Subtype, Type) are intentionally omitted from
the mapping — the generic :class:`CSVImporter` will warn about them but the
data is not lost because the user can always re-export from CLZ with their
own mapping if needed.
"""

from __future__ import annotations

from tangible.importers.csv_importer import CSVImporter


# ---------------------------------------------------------------------------
# Shared columns present in every CLZ CSV export
# ---------------------------------------------------------------------------

_COMMON_MAPPING: dict[str, str] = {
    "Title": "title",
    "Description": "notes",
    "Notes": "subtitle",
    "Condition": "condition",
    "Quantity": "quantity",
    "Purchase Price": "purchase_price",
    "Value": "current_value",
    "Location": "location",
    "Barcode": "id:barcode",
    "Serial No.": "id:serial_no",
    "Index": "id:clz_index",
    "Edition": "attr:edition",
    "My Rating": "attr:my_rating",
    "Collection Status": "attr:collection_status",
    "Completed": "attr:completed",
    "Completed Date": "attr:completed_date",
    "Tags": "attr:tags",
    "Storage Device": "attr:storage_device",
    "Storage Slot": "attr:storage_slot",
    "Purchase Date": "attr:purchase_date",
    "Purchase Store": "attr:purchase_store",
}


# ---------------------------------------------------------------------------
# CLZ Games CSV
# ---------------------------------------------------------------------------

_GAMES_MAPPING: dict[str, str] = {
    **_COMMON_MAPPING,
    "Platform": "attr:platform",
    "Publisher": "attr:publisher_name",
    "Developer": "attr:developer",
    "Release Year": "attr:year",
    "Audience Rating": "attr:rating",
    "Genre": "attr:genre",
    "Series": "attr:series",
    "Format": "attr:format",
    "Region": "attr:region",
    "Box": "attr:box_included",
    "Completeness": "attr:completeness",
    "Manual": "attr:manual_included",
    "Hardware Type": "attr:hardware_type",
}


class CLZCSVGamesImporter(CSVImporter):
    """Pre-wired importer for CLZ Games CSV exports."""

    name: str = "clz-csv-games"

    def __init__(self) -> None:
        super().__init__(
            default_category_slug="games.software",
            mapping=_GAMES_MAPPING,
        )


# ---------------------------------------------------------------------------
# CLZ Movies CSV
# ---------------------------------------------------------------------------

_MOVIES_MAPPING: dict[str, str] = {
    **_COMMON_MAPPING,
    "Release Year": "attr:year",
    "Studio": "attr:studio",
    "Director": "attr:director",
    "Genre": "attr:genre",
    "Series": "attr:series",
    "Format": "attr:format",
    "Region": "attr:region",
    "Audience Rating": "attr:rating",
    "Runtime": "attr:runtime",
    "Aspect Ratio": "attr:aspect_ratio",
    "UPC": "id:upc",
    "Disc Count": "attr:disc_count",
}


class CLZCSVMoviesImporter(CSVImporter):
    """Pre-wired importer for CLZ Movie Collector CSV exports."""

    name: str = "clz-csv-movies"

    def __init__(self) -> None:
        super().__init__(
            default_category_slug="movies.dvd",
            mapping=_MOVIES_MAPPING,
        )


# ---------------------------------------------------------------------------
# CLZ Music CSV
# ---------------------------------------------------------------------------

_MUSIC_MAPPING: dict[str, str] = {
    **_COMMON_MAPPING,
    "Artist": "attr:artist",
    "Label": "attr:label",
    "Catalog #": "attr:catalog_no",
    "Release Year": "attr:year",
    "Genre": "attr:genre",
    "Format": "attr:format",
    "Country": "attr:country",
    "Pressing Year": "attr:pressing_year",
    "Color Vinyl": "attr:color_vinyl",
    "Matrix / Runout": "attr:matrix",
    "Disc Count": "attr:disc_count",
}


class CLZCSVMusicImporter(CSVImporter):
    """Pre-wired importer for CLZ Music Collector CSV exports."""

    name: str = "clz-csv-music"

    def __init__(self) -> None:
        super().__init__(
            default_category_slug="music.cd",
            mapping=_MUSIC_MAPPING,
        )


# ---------------------------------------------------------------------------
# CLZ Books CSV
# ---------------------------------------------------------------------------

_BOOKS_MAPPING: dict[str, str] = {
    **_COMMON_MAPPING,
    "Author": "attr:author",
    "Publisher": "attr:publisher",
    "Release Year": "attr:year",
    "Genre": "attr:genre",
    "Series": "attr:series",
    "Format": "attr:format",
    "Language": "attr:language",
    "ISBN": "id:isbn",
    "Pages": "attr:pages",
    "Signed": "attr:signed",
}


class CLZCSVBooksImporter(CSVImporter):
    """Pre-wired importer for CLZ Book Collector CSV exports."""

    name: str = "clz-csv-books"

    def __init__(self) -> None:
        super().__init__(
            default_category_slug="books.print",
            mapping=_BOOKS_MAPPING,
        )


# ---------------------------------------------------------------------------
# CLZ Comics CSV
# ---------------------------------------------------------------------------

_COMICS_MAPPING: dict[str, str] = {
    **_COMMON_MAPPING,
    "Series": "attr:series",
    "Issue #": "attr:issue_no",
    "Publisher": "attr:publisher",
    "Release Year": "attr:year",
    "Writer": "attr:writer",
    "Artist": "attr:artist",
    "Genre": "attr:genre",
    "Grade": "attr:grade",
    "Graded By": "attr:graded_by",
    "Cert #": "id:cert_number",
    "Variant Cover": "attr:variant_cover",
}


class CLZCSVComicsImporter(CSVImporter):
    """Pre-wired importer for CLZ Comic Collector CSV exports."""

    name: str = "clz-csv-comics"

    def __init__(self) -> None:
        super().__init__(
            default_category_slug="books.comic",
            mapping=_COMICS_MAPPING,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CLZ_CSV_IMPORTERS: dict[str, type[CSVImporter]] = {
    "clz-csv-games": CLZCSVGamesImporter,
    "clz-csv-movies": CLZCSVMoviesImporter,
    "clz-csv-music": CLZCSVMusicImporter,
    "clz-csv-books": CLZCSVBooksImporter,
    "clz-csv-comics": CLZCSVComicsImporter,
}

__all__ = [
    "CLZ_CSV_IMPORTERS",
    "CLZCSVBooksImporter",
    "CLZCSVComicsImporter",
    "CLZCSVGamesImporter",
    "CLZCSVMoviesImporter",
    "CLZCSVMusicImporter",
]
