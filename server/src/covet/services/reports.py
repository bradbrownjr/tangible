"""Report generation service."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.models import Collection, Item, Photo


class CollectionReport:
    """Generate various reports for a collection."""

    def __init__(self, db: DBSession, collection: Collection):
        self.db = db
        self.collection = collection

    def _get_items(self, include_archived: bool = False) -> list[Item]:
        """Get items in the collection."""
        stmt = select(Item).where(Item.collection_id == self.collection.id)
        if not include_archived:
            stmt = stmt.where(Item.archived_at.is_(None))
        return self.db.scalars(stmt.order_by(Item.title)).all()

    def generate_totals(self, include_archived: bool = False) -> dict:
        """Generate collection totals (count, value)."""
        items = self._get_items(include_archived)
        total_value = sum(
            (item.value or Decimal(0)) for item in items
        )
        total_count = len(items)

        return {
            "collection_id": self.collection.id,
            "collection_name": self.collection.name,
            "total_items": total_count,
            "total_value": float(total_value),
            "average_item_value": float(total_value / total_count) if total_count > 0 else 0,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def generate_csv_export(self, include_archived: bool = False) -> str:
        """Generate CSV export of all items."""
        items = self._get_items(include_archived)

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "ID",
                "Title",
                "Subtitle",
                "Category",
                "Value",
                "Quantity",
                "Notes",
                "Archived",
                "Created Date",
            ],
        )
        writer.writeheader()

        for item in items:
            writer.writerow(
                {
                    "ID": item.id,
                    "Title": item.title or "",
                    "Subtitle": item.subtitle or "",
                    "Category": item.category.slug if item.category else "",
                    "Value": item.value or 0,
                    "Quantity": item.quantity or 1,
                    "Notes": item.notes or "",
                    "Archived": "Yes" if item.archived_at else "No",
                    "Created Date": item.created_at.isoformat() if item.created_at else "",
                }
            )

        return output.getvalue()

    def generate_insurance_export(self) -> bytes:
        """Generate insurance-friendly export bundle (ZIP with CSV, photos, documents)."""
        items = self._get_items(include_archived=False)

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add CSV with item data
            csv_content = self.generate_csv_export(include_archived=False)
            zip_file.writestr("items.csv", csv_content)

            # Add manifest with collection info
            manifest = {
                "collection": self.collection.name,
                "exported_at": datetime.utcnow().isoformat(),
                "total_items": len(items),
                "total_value": float(sum(item.value or Decimal(0) for item in items)),
            }
            zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Add photos
            for item in items:
                photos = self.db.scalars(
                    select(Photo).where(Photo.item_id == item.id)
                ).all()
                for photo in photos:
                    if photo.photo_path:
                        try:
                            with open(photo.photo_path, "rb") as f:
                                photo_data = f.read()
                                # Store with a readable path structure
                                zip_path = f"photos/{item.id}/{photo.id}.jpg"
                                zip_file.writestr(zip_path, photo_data)
                        except OSError:
                            # Skip photos that can't be read
                            pass

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    def generate_bom_text(self) -> str:
        """Generate Bill of Materials as text."""
        items = self._get_items(include_archived=False)

        lines = [
            f"BILL OF MATERIALS - {self.collection.name}",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
            f"Total Items: {len(items)}",
            f"Total Value: ${sum(item.value or Decimal(0) for item in items)}",
            "",
            "=" * 80,
            "",
        ]

        # Group by category
        by_category: dict[str, list[Item]] = {}
        for item in items:
            cat = item.category.slug if item.category else "Uncategorized"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        for category in sorted(by_category.keys()):
            lines.append(f"\n{category.upper()}")
            lines.append("-" * 80)
            for item in sorted(by_category[category], key=lambda i: i.title or ""):
                value_str = f"${item.value}" if item.value else "N/A"
                qty_str = f"x{item.quantity}" if item.quantity and item.quantity > 1 else ""
                lines.append(
                    f"  {item.title or 'Untitled':<40} {value_str:>10} {qty_str:>8}"
                )
                if item.subtitle:
                    lines.append(f"    > {item.subtitle}")

        return "\n".join(lines)

    def generate_disposed_items_report(self) -> dict:
        """Generate a report of disposed items (sold, donated, discarded)."""
        # Get all archived items with disposition info
        stmt = (
            select(Item)
            .where(Item.collection_id == self.collection.id)
            .where(Item.archived_at.is_not(None))
            .order_by(Item.disposition_at.desc())
        )
        items = self.db.scalars(stmt).all()

        # Group by disposition type
        by_type: dict[str, list[Item]] = {}
        for item in items:
            dtype = item.disposition_type or "archived"
            if dtype not in by_type:
                by_type[dtype] = []
            by_type[dtype].append(item)

        # Calculate totals
        total_disposed_value = sum(
            (item.disposition_amount or Decimal(0)) for item in items if item.disposition_amount
        )
        total_original_value = sum(
            (item.current_value or Decimal(0)) for item in items
        )

        return {
            "collection_id": self.collection.id,
            "collection_name": self.collection.name,
            "total_disposed": len(items),
            "by_type": {
                dtype: {
                    "count": len(items_list),
                    "total_disposition_value": float(
                        sum(
                            (i.disposition_amount or Decimal(0))
                            for i in items_list
                            if i.disposition_amount
                        )
                    ),
                    "items": [
                        {
                            "id": i.id,
                            "title": i.title,
                            "disposition_at": i.disposition_at.isoformat() if i.disposition_at else None,
                            "disposition_amount": float(i.disposition_amount) if i.disposition_amount else None,
                            "disposition_buyer": i.disposition_buyer,
                            "disposition_note": i.disposition_note,
                            "original_value": float(i.current_value) if i.current_value else None,
                        }
                        for i in sorted(items_list, key=lambda x: x.disposition_at or datetime.min, reverse=True)
                    ],
                }
                for dtype, items_list in sorted(by_type.items())
            },
            "total_disposition_value": float(total_disposed_value),
            "total_original_value": float(total_original_value),
            "generated_at": datetime.utcnow().isoformat(),
        }
