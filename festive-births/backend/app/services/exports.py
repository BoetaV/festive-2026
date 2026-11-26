"""Excel and PDF exports.

v1 used WeasyPrint, which needs GTK/Pango system libraries (painful on Windows and
in slim containers). ReportLab is pure Python, so the PDF works everywhere.

Styling follows the ECDoH campaign artwork: ECDoH green and gold, Montserrat type,
the white disc with a gold ring for the headline figure, and decorative green rings.
"""

import io
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import Delivery, User

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO = ASSETS / "ecdoh-logo.jpg"

# ---- ECDoH brand palette (sampled from the campaign artwork) ----
BRAND = "0B6B3B"                          # Excel header fill
GREEN = colors.HexColor("#0B6B3B")        # ECDoH green
RING = colors.HexColor("#0F7E45")         # decorative ring green
DEEP = colors.HexColor("#0C3B27")         # deep green ink
GOLD = colors.HexColor("#F2B705")         # campaign gold
BLUE = colors.HexColor("#2A5CA8")         # "FACILITIES" blue
TINT = colors.HexColor("#EEF5F0")         # zebra rows
GOLD_TINT = colors.HexColor("#FFF4CC")    # total rows
LINE = colors.HexColor("#DBE4DD")
MUTED = colors.HexColor("#4F6157")
PALE = colors.HexColor("#CFE5D8")


def _register_fonts() -> dict[str, str]:
    """Montserrat (OFL, bundled in assets/fonts); falls back to Helvetica if the files are missing."""
    names = {"regular": "Montserrat-Regular", "semibold": "Montserrat-SemiBold", "bold": "Montserrat-Bold",
             "extrabold": "Montserrat-ExtraBold", "black": "Montserrat-Black"}
    try:
        for name in names.values():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(ASSETS / "fonts" / f"{name}.ttf")))
        pdfmetrics.registerFontFamily("Montserrat", normal=names["regular"], bold=names["bold"],
                                      italic=names["regular"], boldItalic=names["bold"])
        return names
    except Exception:  # pragma: no cover - only if the font files are absent
        return {"regular": "Helvetica", "semibold": "Helvetica-Bold", "bold": "Helvetica-Bold",
                "extrabold": "Helvetica-Bold", "black": "Helvetica-Bold"}


FONT = _register_fonts()


FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _defuse(cell) -> None:
    """Spreadsheet (formula) injection guard: user-typed text such as "=HYPERLINK(...)" must
    land in Excel as plain text, never as a live formula. openpyxl stores any string starting
    with "=" as a formula, and Excel re-evaluates + - @ when a cell is edited."""
    if isinstance(cell.value, str) and cell.value.startswith(FORMULA_START):
        cell.value = "'" + cell.value
        cell.data_type = "s"


def _workbook(title: str, headers: list[str], rows: Iterable[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=BRAND, end_color=BRAND, fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        ws.append(row)
        for cell in ws[ws.max_row]:
            _defuse(cell)
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(
            60, max(len(str(c.value or "")) for c in col) + 2
        )
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def deliveries_xlsx(deliveries: Iterable[Delivery]) -> bytes:
    headers = [
        "Captured At", "Report Date", "Time Slot", "Time of Birth", "District", "Sub-district",
        "Facility", "Facility Type", "Mother Name", "Mother Surname", "Mother D.O.B.", "Mother Age",
        "Gravidity", "Parity", "Birth Mode", "Born Before Arrival", "Baby Number", "Baby Gender",
        "Baby Weight (g)", "Captured By",
    ]

    def rows():
        for d in deliveries:
            common = [
                d.created_at.strftime("%Y-%m-%d %H:%M"), d.report_date, d.time_slot,
                d.delivery_time.strftime("%H:%M") if d.delivery_time else "", d.district,
                d.local_municipality, d.facility, d.facility_type, d.mother_name, d.mother_surname,
                d.mother_dob, d.mother_age, d.gravidity, d.parity, d.birth_mode,
                "Yes" if d.born_before_arrival else "No",
            ]
            by = d.captured_by.persal_number if d.captured_by else "N/A"
            if d.no_births_to_report:
                yield common + ["NIL Report", "", "", by]
            else:
                for i, b in enumerate(d.babies, 1):
                    yield common + [i, b.gender, b.weight, by]

    return _workbook("Festive Births", headers, rows())


def users_xlsx(users: Iterable[User]) -> bytes:
    headers = [
        "Name", "Surname", "Email", "Title", "Designation", "Persal Number", "Mobile Number", "Role",
        "District", "Sub-district", "Facility", "Active", "Must Change Password", "Last Login",
    ]
    rows = (
        [
            u.first_name, u.last_name, u.email, u.title, u.designation, u.persal_number, u.mobile_number,
            u.role.value, u.district, u.local_municipality, u.facility, "Yes" if u.is_active else "No",
            "Yes" if u.must_change_password else "No",
            u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else "",
        ]
        for u in users
    )
    return _workbook("Users", headers, rows)


# ---------------------------------------------------------------- PDF
PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
WHITE_BAND = 28 * mm     # logo band at the top of page 1
GREEN_BAND = 78 * mm     # hero band on page 1
FOOTER_BAND = 11 * mm


def _style(name: str, font: str, size: float, color=DEEP, leading: float | None = None, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=FONT[font], fontSize=size, textColor=color,
                          leading=leading or size * 1.25, **kw)


ST = {
    "cell": _style("cell", "regular", 8.5, colors.black),
    "cell_b": _style("cell_b", "bold", 8.5, DEEP),
    "head": _style("head", "bold", 8.5, colors.white),
    "section": _style("section", "extrabold", 11.5, DEEP),
    "kpi_label": _style("kpi_label", "bold", 6.8, MUTED),
    "kpi_value": _style("kpi_value", "black", 19, GREEN, leading=23),
    "kpi_sub": _style("kpi_sub", "regular", 7, MUTED),
}


def _p(text, style="cell") -> Paragraph:
    return Paragraph(escape(str(text)), ST[style])


def _fmt(n) -> str:
    return "-" if n is None else f"{n:,}".replace(",", " ")


def _table(header: list[str], body: list[list], widths=None, total: list | None = None) -> Table:
    body = body or [["No data for this selection"] + [""] * (len(header) - 1)]
    data = [[_p(header[0], "head")] + header[1:]]
    data += [[_p(r[0])] + list(r[1:]) for r in body]
    if total:
        data.append([_p(total[0], "cell_b")] + list(total[1:]))
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT["regular"]),
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT["bold"]),
        ("FONTNAME", (1, 1), (-1, -1), FONT["regular"]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 2, GOLD),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TINT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if total:
        style += [("FONTNAME", (1, -1), (-1, -1), FONT["bold"]),
                  ("BACKGROUND", (0, -1), (-1, -1), GOLD_TINT),
                  ("TEXTCOLOR", (1, -1), (-1, -1), DEEP),
                  ("LINEABOVE", (0, -1), (-1, -1), 1.2, GREEN)]
    t.setStyle(TableStyle(style))
    return t


def _section(title: str) -> list:
    """Heading with the gold side bar used on the dashboard cards."""
    h = Table([[Paragraph(escape(title), ST["section"])]], colWidths=[CONTENT_W])
    h.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, 0), 3.5, GOLD),
        ("LEFTPADDING", (0, 0), (0, 0), 7),
        ("TOPPADDING", (0, 0), (0, 0), 1),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
    ]))
    return [CondPageBreak(45 * mm), Spacer(1, 5 * mm), h, Spacer(1, 2.5 * mm)]


def _kpi_grid(tiles: list[tuple[str, str, str]]) -> Table:
    """Stat tiles: tracked capitals label, heavy green figure, gold top edge."""
    cols, gap = 4, 3 * mm
    w = (CONTENT_W - gap * (cols - 1)) / cols
    cells = [[Paragraph(escape(label.upper()), ST["kpi_label"]), Paragraph(escape(value), ST["kpi_value"]),
              Paragraph(escape(sub), ST["kpi_sub"])] for label, value, sub in tiles]
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    # Spacer columns between tiles so they read as separate cards.
    data = []
    for r in rows:
        line = []
        for i, c in enumerate(r):
            line.append(c)
            if i < cols - 1:
                line.append("")
        data.append(line)
    widths = []
    for i in range(cols):
        widths.append(w)
        if i < cols - 1:
            widths.append(gap)
    t = Table(data, colWidths=widths, rowHeights=[24 * mm] * len(rows))
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    for ri in range(len(rows)):
        for ci in range(0, len(widths), 2):
            style += [("BACKGROUND", (ci, ri), (ci, ri), colors.white),
                      ("BOX", (ci, ri), (ci, ri), 0.5, LINE),
                      ("LINEABOVE", (ci, ri), (ci, ri), 3, GOLD)]
    t.setStyle(TableStyle(style))
    return t


def _tracked(c, x: float, y: float, text: str, font: str, size: float, space: float, color) -> None:
    """Letter-spaced capitals, like "MILESTONE ACHIEVED" in the artwork."""
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setCharSpace(space)
    t.setFillColor(color)
    t.textOut(text)
    t.setCharSpace(0)  # character spacing is PDF graphics state; reset so later text isn't tracked
    c.drawText(t)


def _tracked_width(text: str, font: str, size: float, space: float) -> float:
    return pdfmetrics.stringWidth(text, font, size) + space * (len(text) - 1)


def _draw_footer(c, page: int) -> None:
    c.setFillColor(GOLD)
    c.rect(0, 0, PAGE_W, FOOTER_BAND, stroke=0, fill=1)
    c.setFillColor(DEEP)
    c.setFont(FONT["extrabold"], 7.5)
    c.drawString(MARGIN, 4.2 * mm, "EASTERN CAPE DEPARTMENT OF HEALTH  ·  CONFIDENTIAL")
    c.drawRightString(PAGE_W - MARGIN, 4.2 * mm, f"PAGE {page}")


def _clip(text: str, font: str, size: float, max_w: float) -> str:
    if pdfmetrics.stringWidth(text, font, size) <= max_w:
        return text
    while text and pdfmetrics.stringWidth(text + "…", font, size) > max_w:
        text = text[:-1]
    return text + "…"


def dashboard_pdf(dash: dict, title: str, generated_by: str, filters: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=18 * mm, bottomMargin=FOOTER_BAND + 8 * mm, title=title,
                            author="Eastern Cape Department of Health")
    k = dash["kpis"]
    pct = lambda v: "-" if v is None else f"{v}%"  # noqa: E731
    totals = ["Total", _fmt(k["males"]), _fmt(k["females"]), _fmt(k["total_births"])]
    shown = {k_: v for k_, v in filters.items() if v}
    if shown.get("Facility"):
        shown.pop("Sub-district", None)  # implied by the facility; keeps the pill on one line
    filt = " · ".join(v.strftime("%d %B %Y") if hasattr(v, "strftime") else str(v)
                      for v in shown.values()) or "All districts · all reporting days"
    generated = f"Generated {datetime.now():%d %B %Y %H:%M} by {generated_by}"
    left_w = PAGE_W - 2 * MARGIN - 75 * mm  # width available left of the disc

    def first_page(c, doc_):
        c.saveState()
        top = PAGE_H
        # White logo band + gold rule
        c.drawImage(str(LOGO), MARGIN, top - WHITE_BAND + 4 * mm, width=62 * mm, height=62 * mm * 112 / 378,
                    preserveAspectRatio=True, mask="auto")
        c.setFillColor(DEEP)
        c.setFont(FONT["black"], 13)
        c.drawRightString(PAGE_W - MARGIN, top - 13 * mm, "FESTIVE BIRTHS")
        sw = _tracked_width("SEASON 2026/27", FONT["bold"], 7.5, 1.2)
        _tracked(c, PAGE_W - MARGIN - sw, top - 18.5 * mm, "SEASON 2026/27", FONT["bold"], 7.5, 1.2, GREEN)
        c.setFillColor(GOLD)
        c.rect(0, top - WHITE_BAND - 2.5 * mm, PAGE_W, 2.5 * mm, stroke=0, fill=1)

        # Green hero band with decorative rings, clipped to the band
        y0 = top - WHITE_BAND - 2.5 * mm - GREEN_BAND
        band_top = y0 + GREEN_BAND
        c.setFillColor(GREEN)
        c.rect(0, y0, PAGE_W, GREEN_BAND, stroke=0, fill=1)
        c.saveState()
        path = c.beginPath()
        path.rect(0, y0, PAGE_W, GREEN_BAND)
        c.clipPath(path, stroke=0, fill=0)
        c.setStrokeColor(RING)
        c.setLineWidth(9 * mm)
        c.circle(PAGE_W + 2 * mm, band_top + 2 * mm, 42 * mm, stroke=1, fill=0)
        c.circle(-8 * mm, y0 - 16 * mm, 38 * mm, stroke=1, fill=0)
        c.restoreState()

        # Left column: eyebrow, title, scope, gold pill, generated-by
        x = MARGIN + 2 * mm
        _tracked(c, x, band_top - 15 * mm, "FESTIVE SEASON 2026/27", FONT["extrabold"], 8.5, 2.2, GOLD)
        c.setFillColor(colors.white)
        c.setFont(FONT["black"], 24)
        c.drawString(x, band_top - 28 * mm, "Festive Season")
        c.drawString(x, band_top - 38 * mm, "Births Report")
        c.setFont(FONT["semibold"], 9.5)
        c.drawString(x, band_top - 46.5 * mm,
                     _clip(title, FONT["semibold"], 9.5, left_w))
        pill = _clip(filt.upper(), FONT["extrabold"], 7.2, left_w)
        pw = pdfmetrics.stringWidth(pill, FONT["extrabold"], 7.2) + 12 * mm
        c.setFillColor(GOLD)
        c.roundRect(x, band_top - 58 * mm, pw, 7.5 * mm, 3.75 * mm, stroke=0, fill=1)
        c.setFillColor(DEEP)
        c.setFont(FONT["extrabold"], 7.2)
        c.drawString(x + 6 * mm, band_top - 55.3 * mm, pill)
        c.setFillColor(PALE)
        c.setFont(FONT["regular"], 7.5)
        c.drawString(x, y0 + 7 * mm, _clip(generated, FONT["regular"], 7.5, left_w))

        # Right column: white disc with gold ring holding the headline figure
        cx, cy, r = PAGE_W - MARGIN - 32 * mm, y0 + GREEN_BAND / 2 + 6 * mm, 24 * mm
        c.setFillColor(RING)
        c.circle(cx, cy, r + 4.5 * mm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.circle(cx, cy, r + 2.2 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.circle(cx, cy, r, stroke=0, fill=1)
        num = _fmt(k["total_births"])
        size = 34 if len(num) <= 4 else 27 if len(num) <= 6 else 21
        c.setFillColor(GREEN)
        c.setFont(FONT["black"], size)
        c.drawCentredString(cx, cy - size * 0.12, num)
        bw = _tracked_width("BIRTHS", FONT["extrabold"], 8.5, 2)
        _tracked(c, cx - bw / 2, cy - 11 * mm, "BIRTHS", FONT["extrabold"], 8.5, 2, BLUE)

        # Male / female split under the disc
        sw, sy = 52 * mm, cy - r - 11 * mm
        total = k["total_births"] or 0
        mw = sw * (k["males"] / total) if total else sw
        c.setFillColor(colors.white)
        c.rect(cx - sw / 2, sy, mw, 2.2 * mm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(cx - sw / 2 + mw, sy, sw - mw, 2.2 * mm, stroke=0, fill=1)
        c.setFont(FONT["bold"], 7.5)
        c.setFillColor(colors.white)
        c.drawString(cx - sw / 2, sy - 4.5 * mm, f'{_fmt(k["males"])} male')
        c.setFillColor(GOLD)
        c.drawRightString(cx + sw / 2, sy - 4.5 * mm, f'{_fmt(k["females"])} female')

        _draw_footer(c, doc_.page)
        c.restoreState()

    def later_pages(c, doc_):
        c.saveState()
        c.setFillColor(GOLD)
        c.rect(0, PAGE_H - 2.5 * mm, PAGE_W, 2.5 * mm, stroke=0, fill=1)
        _tracked(c, MARGIN, PAGE_H - 10 * mm, "FESTIVE SEASON BIRTHS 2026/27", FONT["extrabold"], 8, 1.2, GREEN)
        c.setFillColor(MUTED)
        c.setFont(FONT["regular"], 8)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 10 * mm,
                          _clip(title, FONT["regular"], 8, 95 * mm))
        _draw_footer(c, doc_.page)
        c.restoreState()

    story = [
        Spacer(1, WHITE_BAND + 2.5 * mm + GREEN_BAND - doc.topMargin + 6 * mm),
        _kpi_grid([
            ("Deliveries", _fmt(k["deliveries"]), "Mothers delivered"),
            ("NIL reports", _fmt(k["nil_reports"]), "Time slots with no births"),
            ("Facilities reporting", _fmt(k["facilities_reporting"]), "Births or NIL submitted"),
            ("Average weight", f'{_fmt(k["average_weight"])} g' if k["average_weight"] else "-",
             "Mean birth weight"),
            ("Low birth weight", _fmt(k["low_birth_weight"]), f'{pct(k["low_birth_weight_rate"])} under 2.5 kg'),
            ("Teen births", _fmt(k["teen_births"]), f'{pct(k["teen_birth_rate"])} to mothers aged 10-19'),
            ("Caesarean rate", pct(k["caesarean_rate"]), "Elective + emergency"),
            ("Born before arrival", _fmt(k["born_before_arrival"]),
             f'{_fmt(k["multiple_birth_sets"])} multiple-birth sets'),
        ]),
    ]
    sections = [
        (f'Births per {dash["scope"]["level"].lower()}', dash["by_area"], dash["scope"]["level"]),
        ("Births by mother's age group", dash["age_groups"], "Age group"),
        ("Births by mode of delivery", dash["birth_modes"], "Mode of delivery"),
        ("Births per time slot", dash["time_slots"], "Time slot"),
        ("Births per facility type", dash["facility_types"], "Facility type"),
        ("Births by weight category", dash["weight_bands"], "Weight category"),
    ]
    num_w = 28 * mm
    for heading, items, first_col in sections:
        rows = [[r["name"], _fmt(r["male"]), _fmt(r["female"]), _fmt(r["total"])] for r in items if r["total"]]
        story += _section(heading)
        story.append(_table([first_col, "Male", "Female", "Total"], rows,
                            widths=[CONTENT_W - 3 * num_w, num_w, num_w, num_w], total=totals))

    story += _section("Teenage pregnancies by facility")
    story.append(_table(["Facility", "10-14 yrs", "15-19 yrs"],
                        [[r["facility"], _fmt(r["age_10_14"]), _fmt(r["age_15_19"])]
                         for r in dash["teen_by_facility"]],
                        widths=[CONTENT_W - 2 * num_w, num_w, num_w]))
    story += _section("Multiple births per facility (sets)")
    story.append(_table(["Facility", "Twins", "Triplets", "Quads", "Quints"],
                        [[r["facility"], _fmt(r["twins"]), _fmt(r["triplets"]), _fmt(r["quadruplets"]),
                          _fmt(r["quintuplets"])] for r in dash["multiple_births"]],
                        widths=[CONTENT_W - 4 * 20 * mm] + [20 * mm] * 4))

    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    return buf.getvalue()
