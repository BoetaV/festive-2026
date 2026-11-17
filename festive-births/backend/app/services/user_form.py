"""Printable user account application form for facility users (ECDoH green/gold theme).

The applicant completes and signs it, their supervisor recommends it, and the district
office creates the account on the system and keeps the signed form on file.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .exports import DEEP, FONT, GOLD, GOLD_TINT, GREEN, LOGO, TINT, _tracked, _tracked_width
from .manual_form import S, CheckBox, _fields, _ticks

PAGE_W, PAGE_H = A4
MARGIN = 14 * mm
W = PAGE_W - 2 * MARGIN
HEADER_H = 22 * mm
FOOTER_H = 8 * mm
GAP = 6 * mm


def _section(letter: str, title: str, note: str | None = None) -> Table:
    text = f"{letter}. {title.upper()}"
    if note:
        text += f'  <font name="{FONT["regular"]}" size="7.5" color="#5b6b62">{note}</font>'
    h = Table([[Paragraph(text, S["section"])]], colWidths=[W])
    h.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, 0), 3.5, GOLD), ("LEFTPADDING", (0, 0), (0, 0), 6),
                           ("TOPPADDING", (0, 0), (0, 0), 0), ("BOTTOMPADDING", (0, 0), (0, 0), 1)]))
    return h


def _boxes(n: int, size: float = 6.5 * mm) -> Table:
    """One box per character, e.g. the 8-digit Persal number."""
    t = Table([[""] * n], colWidths=[size] * n, rowHeights=[size])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.8, DEEP)]))
    t.hAlign = "LEFT"
    return t


def _panel(rows: list, background=TINT) -> Table:
    t = Table([[r] for r in rows], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), background), ("LINEBEFORE", (0, 0), (0, -1), 3.5, GOLD),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 1.8), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8)]))
    return t


PAD = 8  # points, inside the boxed blocks
INNER = W - 2 * PAD


def _signature_block(rows: list, background=colors.white) -> Table:
    """Boxed group of write-on fields with a gold top rule."""
    t = Table([[r] for r in rows], colWidths=[W])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, DEEP), ("LINEABOVE", (0, 0), (-1, 0), 3, GOLD),
                           ("BACKGROUND", (0, 0), (-1, -1), background),
                           ("LEFTPADDING", (0, 0), (-1, -1), PAD), ("RIGHTPADDING", (0, 0), (-1, -1), PAD),
                           ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _people(widths=(0.4, 0.25, 0.35)) -> list:
    w = [INNER * x for x in widths]
    return [_fields([("Name and surname", None), ("Persal number", None), ("Designation", None)], w, value_h=6.5 * mm),
            _fields([("Signature", None), ("Date", None), ("Contact number", None)], w, value_h=8 * mm)]


def user_application_pdf() -> bytes:
    """A blank form: everything is completed by hand."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=HEADER_H + 4 * mm, bottomMargin=FOOTER_H + 3 * mm,
                            title="Festive Births user account application",
                            author="Eastern Cape Department of Health")

    def chrome(c, _doc) -> None:
        c.saveState()
        c.drawImage(str(LOGO), MARGIN, PAGE_H - HEADER_H + 3 * mm, width=48 * mm, height=48 * mm * 112 / 378,
                    preserveAspectRatio=True, mask="auto")
        c.setFillColor(DEEP)
        c.setFont(FONT["black"], 14)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 11 * mm, "USER ACCOUNT APPLICATION")
        txt = "FESTIVE SEASON BIRTHS 2026/27 · FACILITY USER ACCESS"
        w = _tracked_width(txt, FONT["bold"], 6.8, 0.9)
        _tracked(c, PAGE_W - MARGIN - w, PAGE_H - 16 * mm, txt, FONT["bold"], 6.8, 0.9, GREEN)
        c.setFillColor(GOLD)
        c.rect(0, PAGE_H - HEADER_H - 1.8 * mm, PAGE_W, 1.8 * mm, stroke=0, fill=1)
        c.rect(0, 0, PAGE_W, FOOTER_H, stroke=0, fill=1)
        c.setFillColor(DEEP)
        c.setFont(FONT["extrabold"], 6.8)
        c.drawString(MARGIN, 3 * mm, "ECDOH · CONFIDENTIAL: CONTAINS PERSONAL INFORMATION (POPIA)")
        c.drawRightString(PAGE_W - MARGIN, 3 * mm, "KEEP THE SIGNED ORIGINAL AT THE DISTRICT OFFICE")
        c.restoreState()

    intro = _panel([Paragraph(
        "<b>Complete this form to get access to the Festive Births system.</b> Write clearly in block letters. "
        "Your supervisor must sign section D before you hand the form to your <b>district office</b>, which "
        "creates the account. You sign in with your <b>Persal number</b> and the default password, which you "
        "must change the first time you sign in.", S["body"])], background=GOLD_TINT)

    titles = _ticks([(t, False) for t in ("Mr", "Ms", "Mrs", "Miss", "Dr", "Prof")], gap=4 * mm, style="cell_b")
    access = Table([[CheckBox(True), Paragraph("Facility user", S["cell_b"]),
                     Paragraph("Own facility's births and reports only", S["small"])]],
                   colWidths=[6 * mm, 26 * mm, None])
    access.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    application = _ticks([("New account", False), ("Change of facility", False), ("Reactivate account", False)],
                         gap=3.5 * mm, style="cell_b")

    declaration = _panel([
        Paragraph("I, the applicant, declare that:", S["cell_b"]),
        Paragraph("1. The information on this form is correct.", S["cell"]),
        Paragraph("2. I will keep my password secret, will not share my account and will sign out after use.",
                  S["cell"]),
        Paragraph("3. I will use patient information only for festive season birth reporting and keep it "
                  "confidential in line with the Protection of Personal Information Act (POPIA).", S["cell"]),
        Paragraph("4. I will tell my supervisor or district office immediately if I think my account has been "
                  "used by someone else, or when I no longer need access.", S["cell"]),
    ])

    supervisor = _signature_block([
        _fields([("Recommendation (tick one)", _ticks([("Recommended", False), ("Not recommended", False)],
                                                      gap=8 * mm, style="cell_b"))], [INNER], value_h=6 * mm),
        *_people(),
    ])
    office = _signature_block([
        _fields([("Account created by (name and surname)", None), ("Persal number", None), ("Signature", None)],
                [INNER * 0.4, INNER * 0.25, INNER * 0.35], value_h=6.5 * mm),
        _fields([("Account created (tick)", _ticks([("Yes", False), ("No", False)], gap=4 * mm, style="cell_b")),
                 ("Date created", None), ("Reason if not created", None)],
                [INNER * 0.4, INNER * 0.25, INNER * 0.35], value_h=6.5 * mm),
    ], background=GOLD_TINT)

    story = [
        intro,
        Spacer(1, 2.5 * mm),
        _section("A", "Applicant details"),
        Spacer(1, 1.5 * mm),
        _fields([("Title (tick one)", titles), ("Persal number", _boxes(8))], [W * 0.55, W * 0.45], value_h=7 * mm),
        Spacer(1, 2 * mm),
        _fields([("First name(s)", None), ("Surname", None)], [W * 0.5, W * 0.5], value_h=7 * mm),
        Spacer(1, 2 * mm),
        _fields([("Designation (job title)", None), ("Mobile number", _boxes(10, 6 * mm))],
                [W * 0.55, W * 0.45], value_h=7 * mm),
        Spacer(1, 2 * mm),
        _fields([("Work e-mail address", None)], [W], value_h=7 * mm),
        Spacer(1, 2.5 * mm),
        _section("B", "Facility allocation"),
        Spacer(1, 1.5 * mm),
        _fields([("District", None), ("Sub-district", None), ("Facility", None)],
                [W * 0.3, W * 0.3, W * 0.4]),
        Spacer(1, 2.5 * mm),
        _fields([("Access requested", access), ("Application type (tick one)", application)],
                [W * 0.4, W * 0.6], value_h=8 * mm),
        Spacer(1, 2.5 * mm),
        KeepTogether([
            _section("C", "Applicant declaration"), Spacer(1, 1.5 * mm), declaration, Spacer(1, 2 * mm),
            _fields([("Applicant signature", None), ("Date", None)], [W * 0.6, W * 0.4], value_h=8 * mm),
        ]),
        Spacer(1, 2.5 * mm),
        KeepTogether([
            _section("D", "Supervisor approval", "facility or operational manager"), Spacer(1, 1.5 * mm),
            supervisor,
        ]),
        Spacer(1, 2.5 * mm),
        KeepTogether([_section("E", "District office use", "account created on the system"), Spacer(1, 1.5 * mm), office]),
    ]
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    return buf.getvalue()
