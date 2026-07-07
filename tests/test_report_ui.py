"""
test_report_ui.py
Unit tests for src/report_ui.py -- the presentation layer used by app/app.py.
Deliberately has no streamlit dependency, so these run in any environment,
including CI systems that don't install the Streamlit UI stack.

Run with:  pytest tests/test_report_ui.py -v -s
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import report_ui
from src.main import process_agreement


def _tags_balanced(html: str, tag: str = "div") -> bool:
    return html.count(f"<{tag}") == html.count(f"</{tag}>")


def test_seal_html_balanced_across_score_range():
    for score, grade in [(0, "F"), (46, "D"), (72, "B"), (100, "A")]:
        html = report_ui.render_seal_html(score, grade)
        assert _tags_balanced(html), f"Unbalanced <div> tags for score={score}, grade={grade}"
        assert str(int(score)) in html
        assert grade in html


def test_seal_uses_correct_grade_family_color():
    # A/B should map to the green family, D/F to red, C to amber
    green_html = report_ui.render_seal_html(90, "A")
    red_html = report_ui.render_seal_html(5, "F")
    assert report_ui.PALETTE["green"]["strong"] in green_html
    assert report_ui.PALETTE["red"]["strong"] in red_html


def test_risk_bar_balanced_and_sums_to_100_percent():
    html = report_ui.render_risk_bar_html(4, 2, 2)
    assert _tags_balanced(html)
    widths = [float(w) for w in re.findall(r"width:([\d.]+)%", html)]
    assert len(widths) == 3
    assert abs(sum(widths) - 100.0) < 0.01, "Risk bar segments should sum to 100%"


def test_risk_bar_handles_zero_clauses_without_division_error():
    html = report_ui.render_risk_bar_html(0, 0, 0)
    assert _tags_balanced(html)


def test_clause_card_balanced_for_every_real_sample_clause():
    for path in ["data/sample_agreement_1.txt", "data/sample_agreement_2.txt", "data/sample_agreement_3.txt"]:
        result = process_agreement(file_path=path, log_result=False, city_tier="metro_tier1")
        for flag in result["flags"]:
            html = report_ui.render_clause_card_html(flag)
            assert _tags_balanced(html), f"Unbalanced card HTML for {path} / {flag['clause_id']}"
            assert "CONFIDENCE" in html, "Confidence badge should be present on every clause card"


def test_locality_line_uses_mono_figures_not_raw_regex_on_text():
    """
    Numbers in the locality line must come from the structured numeric fields
    (rendered via explicit mono spans), not a regex scan over pre-escaped text
    -- the latter risks corrupting HTML entities like &#x27;.
    """
    flag_with_numbers = {
        "risk_level": "yellow", "category": "deposit",
        "locality_comparison": "66.7% higher than typical for Tier-1 Metro (typical: 3 months).",
        "locality_delta_percent": 66.7, "locality_typical_value": 3,
    }
    html = report_ui._render_locality_line(flag_with_numbers)
    assert 'class="rfa-mono-figure"' in html
    assert "66.7%" in html and "3" in html
    assert _tags_balanced(html)

    # fallback path: no numeric fields present, still renders safely
    flag_text_only = {
        "risk_level": "yellow", "category": "deposit",
        "locality_comparison": "Some plain comparison text.",
        "locality_delta_percent": None, "locality_typical_value": None,
    }
    fallback_html = report_ui._render_locality_line(flag_text_only)
    assert _tags_balanced(fallback_html)
    assert "Some plain comparison text." in fallback_html

    # no comparison at all -> empty string, not an error
    assert report_ui._render_locality_line({"locality_comparison": None}) == ""


def test_clause_card_escapes_html_special_characters():
    """A clause card must never let raw HTML/script content through unescaped."""
    tricky_flag = {
        "risk_level": "red",
        "category": "deposit",
        "original_text": 'Rent < 5000 & "non-negotiable" <script>alert(1)</script>',
        "explanation": "Landlord's <b>bold</b> claim applies",
        "locality_comparison": None,
        "needs_human_review": False,
        "suggested_question_to_landlord": "Could we discuss this?",
    }
    html = report_ui.render_clause_card_html(tricky_flag)
    assert "<script>" not in html, "Raw <script> tag leaked into rendered HTML"
    assert "&lt;script&gt;" in html, "Special characters should be HTML-escaped"


def test_hero_and_empty_state_and_section_header_are_balanced():
    assert _tags_balanced(report_ui.render_hero_html())
    empty_html = report_ui.render_empty_state_html()
    assert _tags_balanced(empty_html)
    assert "rfa-empty-features" in empty_html, "Empty state should include the feature preview grid"
    assert empty_html.count("rfa-empty-feature-title") == 4, "Expected 4 feature preview items"
    assert _tags_balanced(report_ui.render_section_header_html("STEP 1", "Title"))


def test_animated_hero_structure_and_safety_guards():
    """
    The animated hero must be self-contained (styles + markup + script all in
    one string, since it's rendered via st.components.v1.html, not st.markdown
    -- see the docstring on render_hero_with_dotted_surface_html for why) and
    must degrade gracefully if the Three.js CDN is blocked or unreachable.
    """
    html = report_ui.render_hero_with_dotted_surface_html()
    assert _tags_balanced(html, "div")
    assert html.count("<script") == html.count("</script>") == 2, "Expected the CDN <script src> tag plus one inline script"
    assert html.count("<style") == html.count("</style>") == 1
    assert "cdnjs.cloudflare.com" in html and "three.min.js" in html
    assert "prefers-reduced-motion" in html, "Must respect reduced-motion preference"
    assert "typeof THREE === 'undefined'" in html, "Must fail gracefully if the CDN script didn't load"
    assert "Rental Agreement Red Flag Report" in html, "Hero title text must still be present"


def test_animated_hero_inline_script_is_valid_javascript():
    """Extracts the inline <script> block and validates it with `node --check` (parse-only)."""
    import re
    import shutil
    import subprocess
    import tempfile

    if shutil.which("node") is None:
        return  # Node not available in this environment; skip rather than fail the suite

    html = report_ui.render_hero_with_dotted_surface_html()
    inline_scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    assert len(inline_scripts) == 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as tmp:
        tmp.write(inline_scripts[0])
        tmp_path = tmp.name

    result = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Invalid JavaScript syntax: {result.stderr}"


def test_clause_count_chip_is_balanced_and_shows_mono_figure():
    html = report_ui.render_clause_count_html(8)
    assert _tags_balanced(html)
    assert "rfa-mono-figure" in html
    assert "8" in html


def test_css_block_is_well_formed():
    assert report_ui.CSS_BLOCK.count("<style>") == report_ui.CSS_BLOCK.count("</style>") == 1
    # spot-check a few classes that app.py actually references exist in the stylesheet
    for class_name in [".rfa-hero", ".rfa-seal", ".rfa-clause-card", ".rfa-riskbar", ".rfa-empty"]:
        assert class_name in report_ui.CSS_BLOCK, f"Missing expected class {class_name} in CSS_BLOCK"


def test_markdown_report_contains_key_facts_and_every_clause():
    result = process_agreement(file_path="data/sample_agreement_2.txt", log_result=False, city_tier="metro_tier1")
    md = report_ui.build_markdown_report(result, "Tier-1 Metro")
    assert str(result["fairness_score"]["score"]) in md
    assert "Tier-1 Metro" in md
    for flag in result["flags"]:
        assert flag["clause_id"] in md


def test_csv_report_has_one_row_per_clause_and_key_columns():
    import csv
    import io

    result = process_agreement(file_path="data/sample_agreement_2.txt", log_result=False, city_tier="metro_tier1")
    csv_text = report_ui.build_csv_report(result)

    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(rows) == len(result["flags"]), "CSV should have exactly one row per clause"

    expected_columns = {
        "clause_id", "category", "risk_level", "confidence", "reason",
        "explanation", "locality_comparison", "needs_human_review",
        "suggested_question_to_landlord",
    }
    assert expected_columns.issubset(set(rows[0].keys()))

    # every clause_id from the pipeline should appear exactly once in the CSV
    csv_ids = {row["clause_id"] for row in rows}
    pipeline_ids = {f["clause_id"] for f in result["flags"]}
    assert csv_ids == pipeline_ids


if __name__ == "__main__":
    test_seal_html_balanced_across_score_range()
    test_seal_uses_correct_grade_family_color()
    test_risk_bar_balanced_and_sums_to_100_percent()
    test_risk_bar_handles_zero_clauses_without_division_error()
    test_clause_card_balanced_for_every_real_sample_clause()
    test_locality_line_uses_mono_figures_not_raw_regex_on_text()
    test_clause_card_escapes_html_special_characters()
    test_hero_and_empty_state_and_section_header_are_balanced()
    test_animated_hero_structure_and_safety_guards()
    test_animated_hero_inline_script_is_valid_javascript()
    test_clause_count_chip_is_balanced_and_shows_mono_figure()
    test_css_block_is_well_formed()
    test_markdown_report_contains_key_facts_and_every_clause()
    test_csv_report_has_one_row_per_clause_and_key_columns()
    print("All report_ui tests passed.")
