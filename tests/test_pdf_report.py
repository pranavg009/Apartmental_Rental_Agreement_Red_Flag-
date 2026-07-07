"""
test_pdf_report.py
Unit tests for src/pdf_report.py. Requires reportlab (a required dependency,
see requirements.txt) to build PDFs, and pypdf to read them back and confirm
real content made it in -- not just that the bytes look like a PDF.

Run with:  pytest tests/test_pdf_report.py -v -s
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import pdf_report
from src.main import process_agreement

try:
    from pypdf import PdfReader
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False


def _extract_text(pdf_bytes: bytes) -> str:
    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "".join(page.extract_text() or "" for page in reader.pages)


def test_pdf_starts_with_valid_header_for_every_sample():
    for path in ["data/sample_agreement_1.txt", "data/sample_agreement_2.txt", "data/sample_agreement_3.txt"]:
        result = process_agreement(file_path=path, log_result=False, city_tier="metro_tier1")
        pdf_bytes = pdf_report.build_pdf_report(result, "Tier-1 Metro")
        assert pdf_bytes[:5] == b"%PDF-", f"Generated file for {path} is not a valid PDF"
        assert len(pdf_bytes) > 1000, f"Generated PDF for {path} looks suspiciously small"


def test_pdf_contains_expected_content():
    if not HAVE_PYPDF:
        print("pypdf not installed -- skipping content-extraction check")
        return
    result = process_agreement(file_path="data/sample_agreement_2.txt", log_result=False, city_tier="metro_tier1")
    pdf_bytes = pdf_report.build_pdf_report(result, "Tier-1 Metro")
    text = _extract_text(pdf_bytes)

    assert "Fairness Report" in text
    assert str(result["fairness_score"]["score"]) in text
    assert f"GRADE {result['fairness_score']['grade']}" in text
    for flag in result["flags"]:
        assert flag["clause_id"] in text


def test_pdf_generation_survives_special_characters():
    """HTML/XML special characters in clause text must not crash reportlab's markup parser."""
    tricky_result = {
        "fairness_score": {"score": 50, "grade": "C", "summary": "Mixed & tricky <case>",
                            "red_count": 1, "yellow_count": 0, "green_count": 0},
        "clauses_found": 1,
        "disclaimer": "Test disclaimer with & < > characters",
        "flags": [{
            "clause_id": "C1", "category": "deposit", "risk_level": "red",
            "original_text": 'Rent < 5000 & "non-negotiable" <script>alert(1)</script>',
            "explanation": "Landlord's <b>bold</b> claim & <injection> attempt",
            "confidence": 0.9, "needs_human_review": True,
            "locality_comparison": "50% higher & weird <tag>",
            "suggested_question_to_landlord": "Could we discuss <this> & that?",
        }],
    }
    pdf_bytes = pdf_report.build_pdf_report(tricky_result, "Test City & Region")
    assert pdf_bytes[:5] == b"%PDF-"

    if HAVE_PYPDF:
        text = _extract_text(pdf_bytes)
        # the literal special characters should appear as plain text, not break parsing
        assert "non-negotiable" in text
        assert "Test City & Region" in text


if __name__ == "__main__":
    test_pdf_starts_with_valid_header_for_every_sample()
    test_pdf_contains_expected_content()
    test_pdf_generation_survives_special_characters()
    print("All pdf_report tests passed.")
