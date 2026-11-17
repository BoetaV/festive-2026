"""Printable manual submission form for facilities without connectivity.

The facility completes it on paper during the reporting day and sends it to the district
office, which captures each row on the system. Same fields as the online capture screen,
in the ECDoH green/gold theme (landscape A4 so the register has room for handwriting).
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, FrameBreak, KeepInFrame, KeepTogether,
                                PageTemplate, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

from ..schemas import BIRTH_MODES, TIME_SLOTS
from .exports import DEEP, FONT, GOLD, GOLD_TINT, GREEN, LINE, LOGO, MUTED, TINT, _tracked, _tracked_width

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 12 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
HEADER_H = 22 * mm
FOOTER_H = 9 * mm

MODE_CODES = {
    "Normal Vertex": "NV",
    "Caesarean section Elective": "CS-EL",
    "Caesarean section Emergency": "CS-EM",
    "Vacuum": "VAC",
    "Forceps": "FOR",
    "Vaginal Breech": "VB",
}
assert set(MODE_CODES) == set(BIRTH_MODES), "keep the paper codes in step with the capture screen"


def _st(name: str, font: str, size: float, color=DEEP, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=FONT[font], fontSize=size, textColor=color,
                          leading=kw.pop("leading", size * 1.25), **kw)


S = {
    "body": _st("body", "regular", 8.5, colors.black),
    "small": _st("small", "regular", 7, MUTED),
    "label": _st("label", "bold", 6.8, MUTED),
    "value": _st("value", "bold", 10, DEEP),
    "section": _st("section", "extrabold", 10.5, DEEP),
    "head": _st("head", "bold", 7, colors.white, alignment=1),
    "head_l": _st("head_l", "bold", 7, colors.white),
    "cell": _st("cell", "regular", 8, colors.black),
    "cell_b": _st("cell_b", "bold", 8, DEEP),
}


class CheckBox(Flowable):
    """Empty (or ticked) tick box for paper forms."""

    def __init__(self, checked: bool = False, size: float = 3.8 * mm):
        super().__init__()
        self.checked, self.size = checked, size
        self.width = self.height = size

    def draw(self):
        c, s = self.canv, self.size
        c.setStrokeColor(DEEP)
        c.setLineWidth(0.9)
        c.rect(0, 0, s, s, stroke=1, fill=0)
        if self.checked:
            c.setLineWidth(1.4)
            c.line(s * 0.2, s * 0.5, s * 0.42, s * 0.22)
            c.line(s * 0.42, s * 0.22, s * 0.82, s * 0.82)


def _ticks(options: list[tuple[str, bool]], gap: float = 6 * mm, style: str = "value") -> Table:
    """A row of tick boxes with labels: [ ] 25 December 2026   [ ] 01 January 2027"""
    st = S[style]
    row, widths = [], []
    for label, checked in options:
        row += [CheckBox(checked), Paragraph(label, st)]
        widths += [6 * mm, pdfmetrics.stringWidth(label, st.fontName, st.fontSize) + gap]
    t = Table([row], colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    t.hAlign = "LEFT"
    return t


def _section(letter: str, title: str) -> Table:
    h = Table([[Paragraph(f"{letter}. {title.upper()}", S["section"])]], colWidths=[CONTENT_W])
    h.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, 0), 3.5, GOLD), ("LEFTPADDING", (0, 0), (0, 0), 6),
                           ("TOPPADDING", (0, 0), (0, 0), 0), ("BOTTOMPADDING", (0, 0), (0, 0), 1)]))
    return h


def _fields(cells: list[tuple[str, object]], widths: list[float], value_h: float = 8 * mm) -> Table:
    """Label above a write-on line. A value may be pre-filled text or any flowable."""
    gap = 6 * mm if len(cells) > 1 else 0
    labels, values, col_w = [], [], []
    for i, ((label, v), w) in enumerate(zip(cells, widths)):
        last = i == len(cells) - 1
        labels.append(Paragraph(label.upper(), S["label"]))
        values.append(Paragraph(v, S["value"]) if isinstance(v, str) else (v if v is not None else ""))
        col_w.append(w if last else w - gap)
        if not last:
            labels.append("")
            values.append("")
            col_w.append(gap)
    t = Table([labels, values], colWidths=col_w, rowHeights=[None, value_h])
    style = [
        ("VALIGN", (0, 0), (-1, 0), "BOTTOM"), ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]
    for col in range(0, len(col_w), 2):  # write-on line under each field, not under the gaps
        style.append(("LINEBELOW", (col, 1), (col, 1), 0.8, DEEP))
    t.setStyle(TableStyle(style))
    return t


def _grid_style(header_rows: int) -> list:
    return [
        ("FONTNAME", (0, 0), (-1, -1), FONT["regular"]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), GREEN),
        ("LINEBELOW", (0, header_rows - 1), (-1, header_rows - 1), 2, GOLD),
        ("GRID", (0, header_rows), (-1, -1), 0.5, LINE),
        ("BOX", (0, 0), (-1, -1), 0.8, DEEP),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]


def _time_slots() -> Table:
    data = [[Paragraph("TIME SLOT", S["head_l"]), Paragraph("BIRTHS RECORDED", S["head"]),
             Paragraph("NIL (NO BIRTHS)", S["head"]), Paragraph("NUMBER OF BIRTHS", S["head"])]]
    for slot in TIME_SLOTS:
        data.append([Paragraph(slot.replace(" - ", " – "), S["cell_b"]), CheckBox(), CheckBox(), ""])
    t = Table(data, colWidths=[38 * mm, 30 * mm, 30 * mm, 32 * mm], rowHeights=[None] + [8 * mm] * len(TIME_SLOTS))
    t.setStyle(TableStyle(_grid_style(1) + [("ALIGN", (1, 1), (2, -1), "CENTER"),
                                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TINT])]))
    return t


def _legend() -> Table:
    modes = "  ·  ".join(f"<b>{code}</b> {name}" for name, code in MODE_CODES.items())
    rows = [
        [Paragraph("HOW TO FILL IN THE REGISTER", S["label"])],
        [Paragraph(f"<b>Mode of delivery:</b> {modes}", S["small"])],
        [Paragraph("<b>Sex:</b> M = male, F = female  ·  <b>BBA:</b> Y = born before arrival, N = born at facility",
                   S["small"])],
        [Paragraph("<b>Weight:</b> in grams, e.g. 3200  ·  <b>Time:</b> 24-hour clock, e.g. 14:35  ·  "
                   "<b>Date of birth:</b> dd/mm/yyyy", S["small"])],
        [Paragraph("<b>Twins / triplets:</b> one row for the mother; complete Baby 2 and Baby 3. "
                   "More than three babies: continue on the next row and write “same mother”.", S["small"])],
    ]
    t = Table(rows, colWidths=[CONTENT_W - 130 * mm - 8 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT), ("LINEBEFORE", (0, 0), (0, -1), 3, GOLD),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return t


def _register(rows: int) -> Table:
    h = lambda t: Paragraph(t, S["head"])  # noqa: E731
    top = [h("NO."), h("BIRTH FORM NO."), h("TIME OF DELIVERY"), h("MOTHER'S NAME"), h("MOTHER'S SURNAME"), h("MOTHER'S DATE OF BIRTH"),
           h("GRAV."), h("PARA"), h("MODE (CODE)"), h("BBA Y/N"),
           h("BABY 1"), "", h("BABY 2"), "", h("BABY 3"), "", h("CAPTURED<br/>(DISTRICT)")]
    sub = ["", "", "", "", "", "", "", "", "", "", h("SEX"), h("WEIGHT (G)"), h("SEX"), h("WEIGHT (G)"),
           h("SEX"), h("WEIGHT (G)"), ""]
    widths = [9, 14, 17, 34, 34, 22, 11, 11, 15, 11, 10, 16, 10, 16, 10, 16, 19]
    scale = CONTENT_W / (sum(widths) * mm)
    widths = [w * mm * scale for w in widths]
    body = [[Paragraph(str(i), S["cell_b"])] + [""] * 15 + [CheckBox()] for i in range(1, rows + 1)]
    t = Table([top, sub] + body, colWidths=widths, repeatRows=2,
              rowHeights=[None, None] + [8.6 * mm] * rows)
    style = _grid_style(2) + [
        ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, TINT]),
        ("ALIGN", (0, 2), (0, -1), "CENTER"), ("ALIGN", (-1, 2), (-1, -1), "CENTER"),
        # Baby columns: shared heading over Sex | Weight, a heavier rule between babies
        ("SPAN", (10, 0), (11, 0)), ("SPAN", (12, 0), (13, 0)), ("SPAN", (14, 0), (15, 0)),
        ("LINEBEFORE", (10, 0), (10, -1), 1.2, DEEP), ("LINEBEFORE", (12, 0), (12, -1), 1.2, DEEP),
        ("LINEBEFORE", (14, 0), (14, -1), 1.2, DEEP), ("LINEBEFORE", (16, 0), (16, -1), 1.2, DEEP),
        ("BACKGROUND", (16, 2), (16, -1), GOLD_TINT),
    ]
    for col in (*range(0, 10), 16):  # single-level headings span both header rows
        style.append(("SPAN", (col, 0), (col, 1)))
    t.setStyle(TableStyle(style))
    return t


def _totals() -> Table:
    cells = [("Deliveries (mothers)", None), ("Babies born", None), ("Male", None), ("Female", None),
             ("Born before arrival", None), ("Time slots with NIL", None)]
    return _fields(cells, [CONTENT_W / 6] * 6, value_h=9 * mm)


def _signoff() -> Table:
    w = (CONTENT_W - 2 * 6 * mm) / 3

    def block(title: str, lines: list[str]) -> Table:
        rows = [[Paragraph(title, S["section"])]]
        for line in lines:
            rows.append([_fields([(line, None)], [w - 10 * mm], value_h=6.5 * mm)])
        b = Table(rows, colWidths=[w])
        b.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, DEEP), ("LINEABOVE", (0, 0), (-1, 0), 3, GOLD),
                               ("BACKGROUND", (0, 0), (-1, 0), TINT),
                               ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        return b

    outer = Table([[
        block("Completed by (facility)", ["Name and surname", "Persal number", "Designation",
                                          "Signature", "Date and time"]),
        "",
        block("Verified by (facility manager)", ["Name and surname", "Persal number",
                                                                "Signature", "Date and time"]),
        "",
        block("Received and captured by (district)", ["Name and surname", "Persal number",
                                                       "Date and time received", "Date captured on system",
                                                       "Signature"]),
    ]], colWidths=[w, 6 * mm, w, 6 * mm, w])
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return outer


def _numbered_canvas(header_footer):
    """Canvas that knows the total page count, so every page can say 'Page X of Y'."""

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                header_footer(self, self._pageNumber, total)
                super().showPage()
            super().save()

    return NumberedCanvas


def manual_form_pdf(*, district: str | None, local_municipality: str | None, facility: str | None,
                    facility_type: str | None, report_date: date | None, report_dates: list[date],
                    rows: int, generated_by: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(PAGE_W, PAGE_H), leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=HEADER_H + 5 * mm, bottomMargin=FOOTER_H + 6 * mm,
                            title="Festive Births manual submission form",
                            author="Eastern Cape Department of Health")
    day_label = report_date.strftime("%d %B %Y") if report_date else None

    def header_footer(c, page: int, total: int) -> None:
        c.saveState()
        # Header: logo, form title, gold rule
        c.drawImage(str(LOGO), MARGIN, PAGE_H - HEADER_H + 3 * mm, width=50 * mm, height=50 * mm * 112 / 378,
                    preserveAspectRatio=True, mask="auto")
        c.setFillColor(DEEP)
        c.setFont(FONT["black"], 15)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 11 * mm, "MANUAL SUBMISSION FORM")
        txt = "FESTIVE SEASON BIRTHS 2026/27 · FOR USE WHEN THE SYSTEM IS OFFLINE"
        w = _tracked_width(txt, FONT["bold"], 7, 1)
        _tracked(c, PAGE_W - MARGIN - w, PAGE_H - 16.5 * mm, txt, FONT["bold"], 7, 1, GREEN)
        c.setFillColor(GOLD)
        c.rect(0, PAGE_H - HEADER_H - 1.8 * mm, PAGE_W, 1.8 * mm, stroke=0, fill=1)
        # Footer: gold band; facility + date on every page keeps loose pages together
        c.setFillColor(GOLD)
        c.rect(0, 0, PAGE_W, FOOTER_H, stroke=0, fill=1)
        c.setFillColor(DEEP)
        c.setFont(FONT["extrabold"], 7)
        c.drawString(MARGIN, 3.4 * mm, "ECDOH · CONFIDENTIAL: CONTAINS PATIENT INFORMATION (POPIA)")
        c.setFont(FONT["bold"], 7.5)
        fac = f"FACILITY: {facility.upper()}" if facility else "FACILITY: ______________________________"
        day = f"DATE: {day_label.upper()}" if day_label else "DATE: ____________________"
        c.drawCentredString(PAGE_W / 2 + 15 * mm, 3.4 * mm, f"{fac}     {day}")
        c.setFont(FONT["extrabold"], 7.5)
        c.drawRightString(PAGE_W - MARGIN, 3.4 * mm, f"PAGE {page} OF {total}")
        c.restoreState()

    intro = Table([[Paragraph(
        "<b>Use this form only when the Festive Births system cannot be reached.</b> It is the end-of-day "
        "summary: send each birth to the district <b>immediately</b> on a Birth notification form, then list "
        "<b>every</b> birth here (one row per mother) with its birth form number, tick NIL for any time slot "
        "with no births and send this register to the district at the end of the day (e-mail, WhatsApp photo "
        "or fax, as arranged with your district). The district captures only rows not already captured from "
        "a birth form and ticks each one. Keep the original at the facility for audit.", S["body"])]],
        colWidths=[CONTENT_W])
    intro.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD_TINT), ("LINEBEFORE", (0, 0), (0, -1), 3.5, GOLD),
                               ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))

    day_options = [(d.strftime("%d %B %Y"), d == report_date) for d in report_dates]
    q = CONTENT_W / 4
    story = [
        intro,
        Spacer(1, 4 * mm),
        _section("A", "Facility details"),
        Spacer(1, 1.5 * mm),
        _fields([("District", district), ("Sub-district", local_municipality), ("Facility", facility),
                 ("Facility type", facility_type)], [q, q, q * 1.25, q * 0.75]),
        Spacer(1, 2 * mm),
        _fields([("Reporting day (tick one)", _ticks(day_options)), ("Contact person", None),
                 ("Facility contact number", None)], [q * 2, q, q]),
        Spacer(1, 4 * mm),
        _section("B", "Time slots and NIL reports"),
        Spacer(1, 1.5 * mm),
    ]
    slots = Table([[_time_slots(), "", _legend()]], colWidths=[130 * mm, 8 * mm, CONTENT_W - 138 * mm])
    slots.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [
        slots,
        Spacer(1, 4 * mm),
        _section("C", "Birth register (one row per mother)"),
        Spacer(1, 1.5 * mm),
        _register(rows),
        Spacer(1, 5 * mm),
        KeepTogether([
            _section("D", "Totals for the day (check against the register)"), Spacer(1, 1.5 * mm), _totals(),
            Spacer(1, 5 * mm),
            _section("E", "Sign-off"), Spacer(1, 2 * mm), _signoff(),
            Spacer(1, 2 * mm),
            Paragraph(f"Form generated from the Festive Births system by {generated_by}. "
                      "Do not photocopy a pre-filled form for a different facility or day.", S["small"]),
        ]),
    ]
    doc.build(story, canvasmaker=_numbered_canvas(header_footer))
    return buf.getvalue()


# ================================================================ birth notification (one per birth)
SLIP_MARGIN = 10 * mm
SLIP_W = A4[0] - 2 * SLIP_MARGIN          # A4 portrait, two forms per page
SLIP_H = A4[1] / 2
SLIP_HEADER = 17 * mm
SLIP_FOOTER = 6.5 * mm


def _birth_slip(*, district, local_municipality, facility, report_date, report_dates) -> list:
    """One complete birth notification: everything the district needs to capture the birth at once."""
    W = SLIP_W
    days = _ticks([(d.strftime("%d %b %Y"), d == report_date) for d in report_dates], gap=4 * mm)
    short = {"Normal Vertex": "Normal vertex", "Caesarean section Elective": "C-section, elective",
             "Caesarean section Emergency": "C-section, emergency", "Vacuum": "Vacuum", "Forceps": "Forceps",
             "Vaginal Breech": "Vaginal breech"}
    col = W * 0.72 / 3
    cells = [[CheckBox(), Paragraph(short[m], S["cell"])] for m in BIRTH_MODES]
    mode_rows = Table([[x for c in cells[i:i + 3] for x in c] for i in (0, 3)],
                      colWidths=[6 * mm, col - 6 * mm] * 3)
    mode_rows.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                   ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))

    def baby():
        b = Table([[CheckBox(), Paragraph("Male", S["cell"]), CheckBox(), Paragraph("Female", S["cell"])],
                   [Paragraph("Weight: ____________ grams", S["cell_b"]), "", "", ""]],
                  colWidths=[6 * mm, 14 * mm, 6 * mm, 16 * mm])
        b.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("SPAN", (0, 1), (-1, 1)),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                               ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
        return b

    district_use = Table([[
        Paragraph("DISTRICT USE", S["label"]),
        _fields([("Received by (name)", None), ("Date and time received", None)], [W * 0.27, W * 0.27],
                value_h=6.5 * mm),
        _ticks([("Captured on system", False)], style="cell_b"),
    ]], colWidths=[W * 0.14, W * 0.58, W * 0.28])
    district_use.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD_TINT),
                                      ("LINEBEFORE", (0, 0), (0, -1), 3, GOLD),
                                      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 3),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))

    gap = 2.2 * mm
    return [
        _fields([("Birth form no. (today)", None), ("Reporting day (tick one)", days),
                 ("Time of delivery (24h, e.g. 00:07)", None)], [W * 0.2, W * 0.5, W * 0.3]),
        Spacer(1, gap),
        _fields([("District", district), ("Sub-district", local_municipality), ("Facility", facility)],
                [W * 0.3, W * 0.3, W * 0.4], value_h=8 * mm),
        Spacer(1, gap),
        _fields([("Mother's name", None), ("Mother's surname", None), ("Mother's date of birth", None),
                 ("Gravida", None), ("Para", None)], [W * 0.27, W * 0.27, W * 0.22, W * 0.12, W * 0.12],
                value_h=9 * mm),
        Spacer(1, gap),
        _fields([("Mode of delivery (tick one)", mode_rows),
                 ("Born before arrival", _ticks([("Yes", False), ("No", False)], gap=4 * mm, style="cell_b"))],
                [W * 0.76, W * 0.24], value_h=12 * mm),
        Spacer(1, gap),
        _fields([("Baby 1", baby()), ("Baby 2 (twins)", baby()), ("Baby 3 (triplets)", baby())],
                [W / 3] * 3, value_h=12 * mm),
        Spacer(1, gap),
        _fields([("Completed by (name and surname)", None), ("Persal number", None), ("Signature", None),
                 ("Date and time sent", None)], [W * 0.32, W * 0.18, W * 0.22, W * 0.28], value_h=9 * mm),
        Spacer(1, 3 * mm),
        district_use,
    ]


def birth_form_pdf(*, district: str | None, local_municipality: str | None, facility: str | None,
                   report_date: date | None, report_dates: list[date], copies: int, generated_by: str) -> bytes:
    """`copies` birth notification forms, two per A4 page with a cut line between them."""
    buf = io.BytesIO()
    page_w, page_h = A4
    body_h = SLIP_H - SLIP_HEADER - SLIP_FOOTER - 9 * mm

    def frame(top: float, ident: str) -> Frame:
        return Frame(SLIP_MARGIN, top - SLIP_HEADER - 3 * mm - body_h, SLIP_W, body_h, id=ident,
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def slip_chrome(c, top: float) -> None:
        bottom = top - SLIP_H
        c.drawImage(str(LOGO), SLIP_MARGIN, top - SLIP_HEADER + 2.5 * mm, width=40 * mm, height=40 * mm * 112 / 378,
                    preserveAspectRatio=True, mask="auto")
        c.setFillColor(DEEP)
        c.setFont(FONT["black"], 14)
        c.drawRightString(page_w - SLIP_MARGIN, top - 9 * mm, "BIRTH NOTIFICATION FORM")
        txt = "ONE FORM PER BIRTH · SEND TO THE DISTRICT IMMEDIATELY AFTER THE BIRTH"
        w = _tracked_width(txt, FONT["bold"], 6.5, 0.8)
        _tracked(c, page_w - SLIP_MARGIN - w, top - 13.5 * mm, txt, FONT["bold"], 6.5, 0.8, GREEN)
        c.setFillColor(GOLD)
        c.rect(0, top - SLIP_HEADER - 1.5 * mm, page_w, 1.5 * mm, stroke=0, fill=1)
        c.rect(0, bottom + 3 * mm, page_w, SLIP_FOOTER, stroke=0, fill=1)
        c.setFillColor(DEEP)
        c.setFont(FONT["extrabold"], 6.5)
        c.drawString(SLIP_MARGIN, bottom + 5.3 * mm, "ECDOH FESTIVE SEASON BIRTHS 2026/27 · CONFIDENTIAL (POPIA)")
        c.drawRightString(page_w - SLIP_MARGIN, bottom + 5.3 * mm,
                          "ALSO LIST THIS BIRTH ON THE END-OF-DAY REGISTER WITH ITS BIRTH FORM NO.")

    def on_page(c, doc_):
        c.saveState()
        slip_chrome(c, page_h)
        slip_chrome(c, page_h / 2)
        # Cut line between the two forms
        c.setStrokeColor(MUTED)
        c.setDash(3, 3)
        c.setLineWidth(0.6)
        c.line(4 * mm, page_h / 2, page_w - 4 * mm, page_h / 2)
        c.setDash()
        c.setFillColor(colors.white)
        c.rect(page_w / 2 - 12 * mm, page_h / 2 - 1.6 * mm, 24 * mm, 3.2 * mm, stroke=0, fill=1)
        c.setFont(FONT["bold"], 6)
        c.setFillColor(MUTED)
        c.drawCentredString(page_w / 2, page_h / 2 - 0.8 * mm, "CUT HERE")
        c.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4, title="Festive Births birth notification forms",
                          author="Eastern Cape Department of Health")
    doc.addPageTemplates([PageTemplate(id="slips", frames=[frame(page_h, "top"), frame(page_h / 2, "bottom")],
                                       onPage=on_page)])
    story = []
    for i in range(copies):
        story.append(KeepInFrame(SLIP_W, body_h, _birth_slip(
            district=district, local_municipality=local_municipality, facility=facility,
            report_date=report_date, report_dates=report_dates), mode="shrink"))
        if i < copies - 1:
            story.append(FrameBreak())
    doc.build(story)
    return buf.getvalue()
