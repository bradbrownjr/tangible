"""Generic CSV importer with caller-supplied column mapping.

The mapping is a dict from CSV header name to a target field name. Target
fields are: ``title``, ``subtitle``, ``notes``, ``condition``, ``quantity``,
``purchase_price``, ``current_value``, ``currency``, ``location``,
``category_slug`` (row-specific category), plus ``id:<name>`` (goes into
``identifiers``), ``attr:<name>`` (goes into ``attrs``), and the reserved
refs ``ref:item_ref`` / ``ref:parent_ref`` for hierarchy round-trips.
Unmapped columns are dropped (with a warning).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import IO

from covet.importers.base import Importer, ImportItem, ImportResult

_NUMERIC = {"purchase_price", "current_value"}
_INT = {"quantity"}
_STRING = {
    "category_slug",
    "title",
    "subtitle",
    "notes",
    "condition",
    "currency",
    "location",
}


@dataclass
class CSVImporter(Importer):
    """CSV → ImportItems given a column mapping."""

    default_category_slug: str | None
    mapping: dict[str, str]
    name: str = "csv"
    encoding: str = "utf-8-sig"  # tolerate BOM-prefixed files
    delimiter: str = ","

    def parse(self, source: IO[bytes]) -> ImportResult:
        text = io.TextIOWrapper(source, encoding=self.encoding, newline="")
        reader = csv.DictReader(text, delimiter=self.delimiter)
        items: list[ImportItem] = []
        warnings: list[str] = []

        if reader.fieldnames is None:
            return ImportResult(items=items, warnings=["empty CSV file"])

        unknown = [c for c in reader.fieldnames if c not in self.mapping]
        if unknown:
            warnings.append(
                f"Ignoring unmapped columns: {', '.join(unknown)}"
            )

        for row_num, row in enumerate(reader, start=2):  # header is line 1
            try:
                item = self._row_to_item(row)
            except (ValueError, KeyError) as exc:
                warnings.append(f"row {row_num}: {exc}")
                continue
            if item is not None:
                items.append(item)
        return ImportResult(items=items, warnings=warnings)

    def _row_to_item(self, row: dict[str, str]) -> ImportItem | None:
        kwargs: dict[str, object] = {}
        if self.default_category_slug:
            kwargs["category_slug"] = self.default_category_slug
        identifiers: dict[str, object] = {}
        attrs: dict[str, object] = {}

        for src, target in self.mapping.items():
            raw = (row.get(src) or "").strip()
            if not raw:
                continue
            if target in _STRING:
                kwargs[target] = raw
            elif target in _INT:
                kwargs[target] = int(raw)
            elif target in _NUMERIC:
                kwargs[target] = float(raw.replace(",", "."))
            elif target.startswith("id:"):
                identifiers[target[3:]] = raw
            elif target.startswith("attr:"):
                attrs[target[5:]] = raw
            elif target == "ref:item_ref":
                identifiers["__csv_item_ref"] = raw
            elif target == "ref:parent_ref":
                identifiers["__csv_parent_ref"] = raw
            else:
                # Unknown target — preserve as attr to avoid data loss.
                attrs[target] = raw

        if "title" not in kwargs:
            return None
        if "category_slug" not in kwargs:
            raise ValueError("category_slug missing (provide default category or map a category column)")
        kwargs["identifiers"] = identifiers
        kwargs["attrs"] = attrs
        return ImportItem(**kwargs)  # type: ignore[arg-type]


__all__ = ["CSVImporter"]
