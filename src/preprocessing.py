"""
preprocessing.py
Cleans raw agreement text and segments it into individual clauses.
"""
import re
from src.utils import Clause


def clean_text(raw_text: str) -> str:
    """Normalize whitespace, strip page-number artifacts, collapse blank lines."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # strip common page-number lines like "Page 1 of 5"
    text = re.sub(r"(?im)^\s*page\s+\d+\s+of\s+\d+\s*$", "", text)
    return text.strip()


# Matches lines like "1. SECURITY DEPOSIT" or "1) Notice Period" at the start of a line
_CLAUSE_HEADING_PATTERN = re.compile(
    r"(?m)^\s*(\d{1,2})[\.\)]\s+([A-Z][A-Za-z /,-]{2,60})\s*$"
)

# Matches "Clause 1:", "Clause 1 -", "CLAUSE 1."
_CLAUSE_WORD_PATTERN = re.compile(
    r"(?im)^\s*clause\s+(\d{1,2})\s*[:.\-]\s*(.{2,60})\s*$"
)

# Matches "ARTICLE I", "Article 1", "ARTICLE 1 - MAINTENANCE"
_ARTICLE_PATTERN = re.compile(
    r"(?im)^\s*article\s+([IVXLCDM\d]{1,6})\s*[:.\-]?\s*(.{0,60})\s*$"
)

# Matches bullet-prefixed headings: "• Security Deposit", "- Notice Period"
_BULLET_HEADING_PATTERN = re.compile(
    r"(?m)^\s*[•\-\*]\s+([A-Z][A-Za-z /,-]{2,60})\s*$"
)

_HEADING_PATTERNS = [
    _CLAUSE_HEADING_PATTERN,
    _CLAUSE_WORD_PATTERN,
    _ARTICLE_PATTERN,
    _BULLET_HEADING_PATTERN,
]


def segment_clauses(cleaned_text: str) -> list[Clause]:
    """
    Split cleaned agreement text into clauses using numbered-heading patterns
    (e.g. "1. SECURITY DEPOSIT"). Falls back to paragraph-based splitting if
    no numbered headings are detected (unstructured agreements).
    """
    matches = []
    for pattern in _HEADING_PATTERNS:
        found = list(pattern.finditer(cleaned_text))
        if len(found) >= 2:  # need at least 2 headings to trust this pattern as the doc's style
            matches = found
            break

    if matches:
        clauses = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned_text)
            clause_text = cleaned_text[start:end].strip()
            if clause_text:
                clauses.append(
                    Clause(
                        clause_id=f"C{i + 1}",
                        original_text=clause_text,
                        start_char=start,
                        end_char=end,
                    )
                )
        return clauses

    # Fallback: split on blank-line-separated paragraphs
    paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]
    clauses = []
    cursor = 0
    for i, para in enumerate(paragraphs):
        start = cleaned_text.find(para, cursor)
        end = start + len(para)
        cursor = end
        clauses.append(
            Clause(clause_id=f"C{i + 1}", original_text=para, start_char=start, end_char=end)
        )
    return clauses
