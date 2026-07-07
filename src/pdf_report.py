"""
pdf_report.py
Generates a downloadable, professionally formatted PDF version of the
fairness report, matching the report_ui.py visual identity (ink navy +
the same semantic red/amber/green risk colors used everywhere else in
the product). Requires reportlab (see requirements.txt).

Kept as its own module, separate from report_ui.py, which has zero external
dependencies by design so the core HTML presentation logic stays testable
without reportlab installed. Only this module needs it, and only when a
user clicks "Download PDF Report".
"""
import io
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK_HEX = "#16233F"
SLATE_HEX = "#5B6472"
BORDER_HEX = "#E3E6EC"
PAPER_HEX = "#F5F6F9"

RISK_HEX = {
    "red": {"strong": "#B3423A", "tint": "#F8E6E4"},
    "yellow": {"strong": "#AD7A17", "tint": "#FBEFD9"},
    "green": {"strong": "#2F7D5C", "tint": "#E3F3EC"},
}
RISK_LABEL = {"red": "RED FLAG", "yellow": "CAUTION", "green": "LOOKS FINE"}
GRADE_TO_FAMILY = {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}


def _styles() -> dict:
    ss = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "rfa_eyebrow", parent=ss["Normal"], textColor=colors.HexColor(SLATE_HEX),
            fontSize=8.5, fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "rfa_title", parent=ss["Title"], textColor=colors.HexColor(INK_HEX),
            fontSize=19, leading=22, spaceAfter=10, alignment=TA_LEFT,
        ),
        "score_big": ParagraphStyle(
            "rfa_score_big", parent=ss["Normal"], fontSize=28, leading=32, fontName="Helvetica-Bold",
        ),
        "score_meta": ParagraphStyle(
            "rfa_score_meta", parent=ss["Normal"], fontSize=10, leading=14, textColor=colors.HexColor(INK_HEX),
        ),
        "section": ParagraphStyle(
            "rfa_section", parent=ss["Heading2"], fontSize=13, leading=16,
            textColor=colors.HexColor(INK_HEX), spaceBefore=14, spaceAfter=8,
        ),
        "clause_head": ParagraphStyle(
            "rfa_clause_head", parent=ss["Normal"], fontSize=11.3, leading=14,
            fontName="Helvetica-Bold", textColor=colors.HexColor(INK_HEX), spaceAfter=4,
        ),
        "quote": ParagraphStyle(
            "rfa_quote", parent=ss["Normal"], fontSize=9, leading=12.5,
            textColor=colors.HexColor(SLATE_HEX), fontName="Helvetica-Oblique", leftIndent=10, spaceAfter=5,
        ),
        "body": ParagraphStyle("rfa_body", parent=ss["Normal"], fontSize=9.6, leading=13.5, spaceAfter=5),
        "review": ParagraphStyle(
            "rfa_review", parent=ss["Normal"], fontSize=9.2, leading=13,
            textColor=colors.HexColor(RISK_HEX["yellow"]["strong"]), spaceAfter=5,
        ),
        "suggest": ParagraphStyle(
            "rfa_suggest", parent=ss["Normal"], fontSize=9.2, leading=13,
            backColor=colors.HexColor(PAPER_HEX), borderPadding=6, spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "rfa_footer", parent=ss["Normal"], fontSize=8, leading=11,
            textColor=colors.HexColor(SLATE_HEX), fontName="Helvetica-Oblique", spaceBefore=12,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _rule(color_hex: str = BORDER_HEX, space_before: float = 0, space_after: float = 10) -> HRFlowable:
    return HRFlowable(width="100%", thickness=1, color=colors.HexColor(color_hex),
                       spaceBefore=space_before, spaceAfter=space_after)


def build_pdf_report(result: dict, city_tier_label: str = None) -> bytes:
    """Render the pipeline's result dict as a PDF and return its raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER, title="Rental Agreement Fairness Report",
        topMargin=0.65 * inch, bottomMargin=0.65 * inch, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = _styles()
    story = []
    fs = result["fairness_score"]

    story.append(_p("HOUSING LITERACY TOOL", styles["eyebrow"]))
    story.append(_p("Rental Agreement Fairness Report", styles["title"]))
    story.append(_rule())

    grade_hex = RISK_HEX[GRADE_TO_FAMILY.get(fs["grade"], "red")]["strong"]
    score_cell = _p(
        f'<font color="{grade_hex}">{fs["score"]}/100</font><br/>'
        f'<font color="{grade_hex}"><b>GRADE {xml_escape(str(fs["grade"]))}</b></font>',
        styles["score_big"],
    )
    meta_lines = [xml_escape(fs["summary"])]
    meta_lines.append(
        f'{fs["red_count"]} red flag(s) &middot; {fs["yellow_count"]} caution &middot; '
        f'{fs["green_count"]} look fine &middot; {result["clauses_found"]} clauses analyzed'
    )
    if city_tier_label:
        meta_lines.append(f"Benchmarked against: {xml_escape(city_tier_label)}")
    meta_cell = _p("<br/>".join(meta_lines), styles["score_meta"])

    header_table = Table([[score_cell, meta_cell]], colWidths=[1.9 * inch, 4.4 * inch])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(_rule())

    story.append(_p("Clause-by-Clause Report", styles["section"]))

    ordering = {"red": 0, "yellow": 1, "green": 2}
    for f in sorted(result["flags"], key=lambda x: ordering[x["risk_level"]]):
        family = f["risk_level"] if f["risk_level"] in RISK_HEX else "yellow"
        strong = RISK_HEX[family]["strong"]
        risk_label = RISK_LABEL.get(f["risk_level"], f["risk_level"].upper())
        category_label = f["category"].replace("_", " ").title()
        confidence_pct = round(f.get("confidence", 0) * 100)

        story.append(_p(
            f'<font color="{strong}"><b>[{risk_label}]</b></font>  '
            f'{xml_escape(f["clause_id"])} &mdash; {xml_escape(category_label)}  '
            f'<font color="{SLATE_HEX}" size="8">(confidence {confidence_pct}%)</font>',
            styles["clause_head"],
        ))
        story.append(_p(xml_escape(f["original_text"]), styles["quote"]))
        story.append(_p(f'<b>What this means:</b> {xml_escape(f["explanation"])}', styles["body"]))
        if f.get("locality_comparison"):
            story.append(_p(f'<b>Regional comparison:</b> {xml_escape(f["locality_comparison"])}', styles["body"]))
        if f.get("needs_human_review"):
            story.append(_p("Low confidence &mdash; recommend a human/legal review of this clause.", styles["review"]))
        story.append(_p(
            f'<b>Suggested message to your landlord:</b> {xml_escape(f["suggested_question_to_landlord"])}',
            styles["suggest"],
        ))

    story.append(_rule(space_before=4, space_after=8))
    story.append(_p(xml_escape(result["disclaimer"]), styles["footer"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
