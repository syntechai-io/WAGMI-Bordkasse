"""Maintenance & warranty timeline PDF export.

A dated, evidence-grade record of service, repair, inspection, and warranty
work — the kind of thing you hand to a yard or manufacturer in a warranty
dispute instead of a folder of loose invoices."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from typing import Any, Dict, List, Optional

CATEGORY_LABELS_DE = {
    "service": "Wartung",
    "repair": "Reparatur",
    "inspection": "Inspektion",
    "warranty_claim": "Garantiefall",
}
STATUS_LABELS_DE = {
    "open": "Offen",
    "in_progress": "In Bearbeitung",
    "resolved": "Erledigt",
}


def render_maintenance_pdf(
    records: List[Any],
    boat_name: str,
    boat_stats: Dict[str, Any],
    outfile: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Render a maintenance/warranty timeline PDF.

    Args:
        records: MaintenanceRecord objects, newest first (as returned by
            services.maintenance.list_records_for_account).
        boat_name: Boat name for the header.
        boat_stats: dict with total_nm / total_motor_h / trip_count / last_trip,
            from services.boat.compute_boat_stats — shown as a summary block.
        outfile: file-like object to write the PDF into.
        meta: optional {'title', 'creator'} PDF metadata.
    """
    doc = SimpleDocTemplate(
        outfile,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=(meta or {}).get("title", "Wartungslog"),
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MaintTitle", parent=styles["Title"], alignment=TA_LEFT, fontSize=18, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "MaintSub", parent=styles["Normal"], alignment=TA_LEFT, fontSize=10,
        textColor=colors.HexColor("#4d6470"), spaceAfter=10,
    )
    cell_style = ParagraphStyle("MaintCell", parent=styles["Normal"], fontSize=8, leading=10)
    header_style = ParagraphStyle(
        "MaintHeader", parent=styles["Normal"], fontSize=8.5, leading=10,
        textColor=colors.white, fontName="Helvetica-Bold",
    )

    story = []
    story.append(Paragraph(f"⚓ {boat_name} — Wartungs- &amp; Garantielog", title_style))
    story.append(Paragraph(
        f"Stand: {boat_stats.get('total_nm', 0)} sm · "
        f"{boat_stats.get('total_motor_h', 0)} Motorstunden · "
        f"{boat_stats.get('trip_count', 0)} Törns",
        sub_style,
    ))
    story.append(Spacer(1, 4 * mm))

    header = [Paragraph(h, header_style) for h in
              ["Datum", "Kategorie", "Titel", "Werft/Firma", "Std.", "sm", "Kosten", "Status", "Notizen"]]
    rows = [header]

    for r in records:
        cost = f"{r.cost_amount:.2f} {r.cost_currency.value}" if r.cost_amount is not None and r.cost_currency else "–"
        rows.append([
            Paragraph(r.performed_at.strftime("%d.%m.%Y") if r.performed_at else "–", cell_style),
            Paragraph(CATEGORY_LABELS_DE.get(r.category, r.category), cell_style),
            Paragraph(r.title or "–", cell_style),
            Paragraph(r.vendor or "–", cell_style),
            Paragraph(f"{r.engine_hours_at:.1f}" if r.engine_hours_at is not None else "–", cell_style),
            Paragraph(f"{r.nm_at:.1f}" if r.nm_at is not None else "–", cell_style),
            Paragraph(cost, cell_style),
            Paragraph(STATUS_LABELS_DE.get(r.status, r.status), cell_style),
            Paragraph((r.notes or "–")[:200], cell_style),
        ])

    if len(rows) == 1:
        rows.append([Paragraph("Noch keine Einträge.", cell_style)] + [Paragraph("", cell_style)] * 8)

    col_widths = [20*mm, 20*mm, 32*mm, 26*mm, 12*mm, 12*mm, 20*mm, 18*mm, 42*mm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12293a")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c6d2ce")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    doc.build(story)
