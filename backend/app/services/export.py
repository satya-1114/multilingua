"""Export engine: CSV, Excel, JSON, and PDF (text-based) generators.

Returns raw bytes plus a suggested MIME type and filename. Consumers
wrap the payload in a ``StreamingResponse`` or persist it to storage
for background export jobs.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Iterable, Sequence

Row = dict[str, object]


def _fields(rows: Sequence[Row], preferred: Sequence[str] | None = None) -> list[str]:
    if preferred:
        keys = list(preferred)
        for r in rows:
            for k in r.keys():
                if k not in keys:
                    keys.append(k)
        return keys
    seen: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.append(k)
    return seen


def to_csv(rows: Sequence[Row], *, fields: Sequence[str] | None = None) -> bytes:
    buf = io.StringIO()
    keys = _fields(rows, fields)
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: _stringify(r.get(k)) for k in keys})
    return buf.getvalue().encode("utf-8")


def to_json(rows: Iterable[Row]) -> bytes:
    return json.dumps(list(rows), default=str, indent=2).encode("utf-8")


def to_excel(rows: Sequence[Row], *, sheet: str = "Sheet1", fields: Sequence[str] | None = None) -> bytes:
    try:
        from openpyxl import Workbook  # type: ignore
    except ImportError:
        # Fallback: emit CSV bytes when openpyxl is unavailable so callers
        # never crash in slim runtimes.
        return to_csv(rows, fields=fields)

    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    keys = _fields(rows, fields)
    ws.append(keys)
    for r in rows:
        ws.append([_stringify(r.get(k)) for k in keys])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(title: str, rows: Sequence[Row], *, fields: Sequence[str] | None = None) -> bytes:
    try:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.pagesizes import A4, landscape  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # type: ignore
    except ImportError:
        return f"{title}\n\n{to_json(rows).decode('utf-8')}".encode("utf-8")

    keys = _fields(rows, fields)
    body = [[Paragraph(str(k), getSampleStyleSheet()["Normal"]) for k in keys]]
    for r in rows[:1000]:  # cap for PDF safety
        body.append([Paragraph(_stringify(r.get(k)), getSampleStyleSheet()["Normal"]) for k in keys])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), title=title)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated {datetime.now(timezone.utc).isoformat()}", styles["Italic"]),
        Spacer(1, 12),
    ]
    if body[1:]:
        table = Table(body, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No data.", styles["Normal"]))
    doc.build(story)
    return buf.getvalue()


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


MIME = {
    "csv": "text/csv",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
    "pdf": "application/pdf",
}


def render(format: str, *, title: str, rows: Sequence[Row], fields: Sequence[str] | None = None) -> tuple[bytes, str, str]:
    fmt = format.lower()
    if fmt == "csv":
        return to_csv(rows, fields=fields), MIME["csv"], f"{title}.csv"
    if fmt == "json":
        return to_json(rows), MIME["json"], f"{title}.json"
    if fmt in {"xlsx", "excel"}:
        return to_excel(rows, fields=fields), MIME["excel"], f"{title}.xlsx"
    if fmt == "pdf":
        return to_pdf(title, rows, fields=fields), MIME["pdf"], f"{title}.pdf"
    raise ValueError(f"Unsupported export format: {format}")
