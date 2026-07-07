"""
heatmap.py
UNIQUE FEATURE: renders the full agreement text as color-coded HTML, with each
clause highlighted green/yellow/red inline -- so the tenant sees risk *in
context* rather than only in an abstract table. This is the single highest
demo-impact feature: it turns a JSON list into something visually intuitive.

Extension note (documented, not required for MVP): for scanned/image PDFs,
this same color-coding can be drawn as bounding boxes directly on the page
image using OCR word coordinates (e.g. pytesseract's `image_to_data`), so the
highlight appears on the original scanned document rather than re-typed text.
That is a natural v2 extension once the text-based heatmap below is working.
"""
import html

_COLORS = {
    "green": "#E3F3EC",
    "yellow": "#FBEFD9",
    "red": "#F8E6E4",
}

_BORDER_COLORS = {
    "green": "#2F7D5C",
    "yellow": "#AD7A17",
    "red": "#B3423A",
}


def build_html_heatmap(cleaned_text: str, flags: list) -> str:
    """
    flags: list of dicts/objects with start_char, end_char, risk_level, category
    (matching the Clause + RiskFlag pairing produced by main.py)
    Returns a self-contained HTML string with inline highlighted spans.
    """
    # Sort flags by position so we can walk the text left to right
    ordered = sorted(flags, key=lambda f: f["start_char"])

    pieces = []
    cursor = 0
    for f in ordered:
        start, end = f["start_char"], f["end_char"]
        if start < cursor:
            continue  # skip overlaps defensively
        pieces.append(html.escape(cleaned_text[cursor:start]))

        color = _COLORS.get(f["risk_level"], "#eeeeee")
        border = _BORDER_COLORS.get(f["risk_level"], "#999999")
        segment = html.escape(cleaned_text[start:end])
        tooltip = html.escape(f"{f['category']} — {f['risk_level'].upper()}: {f.get('reason', '')}")

        pieces.append(
            f'<span title="{tooltip}" style="background-color:{color}; '
            f'border-left: 4px solid {border}; padding: 2px 4px; border-radius: 3px;">'
            f"{segment}</span>"
        )
        cursor = end

    pieces.append(html.escape(cleaned_text[cursor:]))

    legend = (
        '<div style="margin-bottom:12px; font-family:sans-serif; font-size:13px;">'
        '<span style="background:#E3F3EC; padding:2px 8px; border-radius:3px;">Low risk</span>&nbsp;'
        '<span style="background:#FBEFD9; padding:2px 8px; border-radius:3px;">Caution</span>&nbsp;'
        '<span style="background:#F8E6E4; padding:2px 8px; border-radius:3px;">Red flag</span>'
        "</div>"
    )

    body = "".join(pieces).replace("\n", "<br>")
    return (
        f'<div style="font-family: sans-serif; line-height: 1.7; white-space: pre-wrap;">'
        f"{legend}{body}</div>"
    )
