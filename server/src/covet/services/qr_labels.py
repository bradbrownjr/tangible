"""QR code label sheet generation."""

from __future__ import annotations

from io import BytesIO

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _make_qr_png(data: str, size_px: int = 200) -> BytesIO:
    """Generate a QR code PNG for *data* and return it as a BytesIO buffer."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_qr_codes_pdf(
    items: list[dict],
    collection_name: str = "Items",
    labels_per_row: int = 3,
    labels_per_column: int = 4,
) -> bytes:
    """Generate a PDF with QR code labels for items.

    Each QR code encodes ``covet://item/<item_id>`` so that scanning with a
    Covet-aware reader jumps directly to the item.

    Args:
        items: List of dicts with ``id`` and ``title`` keys.
        collection_name: Collection name used in the PDF title.
        labels_per_row: Number of label columns (3 or 4).
        labels_per_column: Number of label rows per page.

    Returns:
        PDF bytes.
    """
    usable_width = 8.5 - 1.0   # 7.5 inches
    usable_height = 11.0 - 1.5  # 9.5 inches

    label_width = usable_width / labels_per_row
    label_height = usable_height / labels_per_column

    # QR image occupies most of the label height, leaving room for the title.
    qr_size = min(label_width - 0.15, label_height - 0.55) * inch

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )

    title_style = ParagraphStyle(
        "Title",
        fontSize=14,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    label_style = ParagraphStyle(
        "Label",
        fontSize=7,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )

    elements = []
    elements.append(Paragraph(f"{collection_name} - QR Code Labels", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    label_data: list[list] = []
    current_row: list = []

    for item in items:
        uri = f"covet://item/{item['id']}"
        qr_buf = _make_qr_png(uri)
        qr_img = RLImage(qr_buf, width=qr_size, height=qr_size)

        title_text = (item.get("title") or "Untitled")[:30]
        label_para = Paragraph(title_text, label_style)

        from reportlab.platypus import KeepTogether
        cell_content = KeepTogether([qr_img, Spacer(1, 2), label_para])
        current_row.append(cell_content)

        if len(current_row) == labels_per_row:
            label_data.append(current_row)
            current_row = []

    if current_row:
        while len(current_row) < labels_per_row:
            current_row.append("")
        label_data.append(current_row)

    if label_data:
        table = Table(
            label_data,
            colWidths=[label_width * inch] * labels_per_row,
            rowHeights=[label_height * inch] * len(label_data),
        )
        table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

