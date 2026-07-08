"""
app.py
Streamlit UI for the Apartment Rental Agreement Red Flag Agent.

Design: "official assessment report" rather than a generic dashboard -- see
src/report_ui.py for the full design system (colors, type, HTML builders).
This file wires that presentation layer to the pipeline in src/main.py and
handles native Streamlit interactivity (buttons, uploads, tabs, expanders).

Run with:  streamlit run app/app.py
(run from the project root so the `src` package resolves correctly)
"""
import os
import sys
import json
import re
import tempfile

import streamlit as st

# Allow running "streamlit run app/app.py" from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import main as pipeline
from src import logger
from src import locality_benchmark
from src import report_ui
from src import pdf_report


def speech_button(text: str, key: str, label: str = "Read Aloud", height: int = 55):
    """
    Voice / Accessibility Mode: Play/Stop control using the browser's built-in
    Web Speech API (speechSynthesis). No server-side TTS library or API key
    needed -- the browser does the speaking. This renders inside a sandboxed
    iframe (st.components.v1.html), so styles here are self-contained and
    don't rely on the page's global CSS.
    """
    safe_key = re.sub(r"\W", "_", key)
    safe_text = json.dumps(text)
    html = f"""
    <div style="font-family: 'Inter', sans-serif; display:flex; align-items:center; gap:8px;">
      <button id="play_{safe_key}" style="padding:6px 12px; border-radius:7px; border:1px solid #16233F;
        background:#16233F; color:#fff; cursor:pointer; font-size:13px; font-weight:600;">🔊 {label}</button>
      <button id="stop_{safe_key}" style="padding:6px 12px; border-radius:7px; border:1px solid #E3E6EC;
        background:#fff; color:#16233F; cursor:pointer; font-size:13px; font-weight:600;">⏹ Stop</button>
      <span id="status_{safe_key}" style="font-size:12px; color:#5B6472;"></span>
    </div>
    <script>
      (function() {{
        const text = {safe_text};
        const playBtn = document.getElementById("play_{safe_key}");
        const stopBtn = document.getElementById("stop_{safe_key}");
        const status = document.getElementById("status_{safe_key}");
        playBtn.addEventListener("click", function() {{
          if (!window.speechSynthesis) {{
            status.innerText = "Speech not supported in this browser.";
            return;
          }}
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.rate = 0.95;
          utterance.onstart = function() {{ status.innerText = "Playing..."; }};
          utterance.onend = function() {{ status.innerText = "Done."; }};
          window.speechSynthesis.speak(utterance);
        }});
        stopBtn.addEventListener("click", function() {{
          if (window.speechSynthesis) {{ window.speechSynthesis.cancel(); }}
          status.innerText = "Stopped.";
        }});
      }})();
    </script>
    """
    st.components.v1.html(html, height=height)


def clause_display_label(flag: dict) -> str:
    """Build the plain-text expander label (Streamlit expander labels can't render HTML)."""
    icon = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(flag["risk_level"], "⚪")
    try:
        clause_num = int(flag["clause_id"].lstrip("C"))
        clause_ref = f"Clause {clause_num}"
    except (ValueError, AttributeError):
        clause_ref = flag["clause_id"]
    category_label = flag["category"].replace("_", " ").title()
    risk_label = report_ui.RISK_LABEL.get(flag["risk_level"], flag["risk_level"].upper())
    return f"{icon}  {clause_ref} — {category_label} — {risk_label}"


st.set_page_config(page_title="Rental Agreement Red Flag Report", page_icon="📑", layout="wide")
st.markdown(report_ui.CSS_BLOCK, unsafe_allow_html=True)
st.components.v1.html(report_ui.render_hero_with_dotted_surface_html(), height=225)

with st.sidebar:
    st.markdown('<div class="rfa-side-eyebrow">Step 1</div><div class="rfa-side-title">Provide your agreement</div>', unsafe_allow_html=True)
    with st.sidebar:
    st.markdown(...)  # Step 1 label, unchanged
    with st.form("analyze_form"):
        input_mode = st.radio(...)
        # ...(file_uploader / text_area / selectbox blocks, unchanged)...
        st.markdown(...)  # Step 2 label, unchanged
        tier_key = st.selectbox(...)
        run_button = st.form_submit_button("Analyze Agreement", type="primary", use_container_width=True)
    input_mode = st.radio(
        "How would you like to provide the agreement?",
        ["📄 Upload file", "✍️ Paste text", "🧪 Try a sample"],
        label_visibility="collapsed",
    )

    file_path = None
    raw_text = None

    if input_mode == "📄 Upload file":
        uploaded = st.file_uploader("Upload agreement (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
        if uploaded is not None:
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getvalue())
                file_path = tmp.name

    elif input_mode == "✍️ Paste text":
        raw_text = st.text_area("Paste agreement text here", height=220, label_visibility="collapsed",
                                 placeholder="Paste the full agreement text here...")

    else:
        sample_choice = st.selectbox(
            "Choose a synthetic sample",
            ["sample_agreement_1.txt (mostly fair)", "sample_agreement_2.txt (mixed)", "sample_agreement_3.txt (predatory)"],
            label_visibility="collapsed",
        )
        sample_filename = sample_choice.split(" ")[0]
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", sample_filename)

    st.markdown('<div class="rfa-side-eyebrow" style="margin-top:18px;">Step 2</div><div class="rfa-side-title">Compare to your region</div>', unsafe_allow_html=True)
    tier_options = {"none": "Skip — don't compare to a region"}
    tier_options.update(locality_benchmark.list_city_tiers())
    tier_key = st.selectbox(
        "Compare your terms against typical values for:",
        options=list(tier_options.keys()),
        format_func=lambda k: tier_options[k],
        label_visibility="collapsed",
    )
    city_tier = None if tier_key == "none" else tier_key

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    run_button = st.button("Analyze Agreement", type="primary", use_container_width=True)

if run_button:
    if not file_path and not raw_text:
        st.warning("Please upload a file, paste text, or select a sample first.")
    else:
        try:
            with st.status("Starting analysis...", expanded=False) as status:
                result = pipeline.process_agreement(
                    file_path=file_path, raw_text=raw_text, city_tier=city_tier,
                    progress_callback=lambda msg: status.update(label=msg),
                )
                status.update(label="Analysis complete", state="complete")
            st.session_state["result"] = result
            st.session_state["city_tier_label"] = tier_options.get(tier_key) if city_tier else None
        except ValueError as e:
            if "NO_TEXT_EXTRACTED" in str(e):
                st.error(
                    "⚠️ We couldn't read any text from this file. This usually means it's "
                    "a scanned or photographed PDF (image only, no selectable text). "
                    "Please try **✍️ Paste text** instead, or upload a digital/text-based PDF or DOCX."
                )
            else:
                st.error(f"Something went wrong while analyzing this agreement: {e}")
            st.session_state.pop("result", None)

if "result" in st.session_state:
    result = st.session_state["result"]
    flags = result["flags"]
    fscore = result["fairness_score"]

    st.markdown(report_ui.render_section_header_html("§01 — Headline Assessment", "Agreement Fairness Score"),
                unsafe_allow_html=True)

    seal_col, detail_col = st.columns([1, 2], gap="large")
    with seal_col:
        st.markdown(report_ui.render_seal_html(fscore["score"], fscore["grade"]), unsafe_allow_html=True)
    with detail_col:
        st.markdown(f"**{fscore['summary']}**")
        st.markdown(report_ui.render_risk_bar_html(fscore["red_count"], fscore["yellow_count"], fscore["green_count"]),
                    unsafe_allow_html=True)
        st.markdown(report_ui.render_clause_count_html(result["clauses_found"]), unsafe_allow_html=True)
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        speech_button(result["audio_summary"], key="full_summary", label="Read Full Summary Aloud")

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    st.markdown(report_ui.render_section_header_html("§02 — Full Detail", "Clause-by-Clause Report"),
                unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Report", "🖍️ Heatmap"])

    with tab1:
        ordering = {"red": 0, "yellow": 1, "green": 2}
        for f in sorted(flags, key=lambda x: ordering[x["risk_level"]]):
            with st.expander(clause_display_label(f)):
                st.markdown(report_ui.render_clause_card_html(f), unsafe_allow_html=True)
                st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
                action_col1, action_col2 = st.columns([2, 1])
                with action_col1:
                    speech_button(f["audio_text"], key=f"clause_{f['clause_id']}", label="Read this clause aloud")
                with action_col2:
                    if st.button("👍 Useful", key=f"useful_{f['clause_id']}", use_container_width=True):
                        logger.log_feedback(result["run_id"], f["clause_id"], True)
                        st.toast("Thanks for the feedback!")

    with tab2:
        st.caption("Clauses highlighted directly in the original text, color-coded by risk.")
        st.components.v1.html(result["heatmap_html"], height=600, scrolling=True)

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    city_tier_label = st.session_state.get("city_tier_label")
    report_md = report_ui.build_markdown_report(result, city_tier_label)
    report_csv = report_ui.build_csv_report(result)
    pdf_bytes = pdf_report.build_pdf_report(result, city_tier_label)

    dl_col1, dl_col2, dl_col3 = st.columns(3)
    with dl_col1:
        st.download_button(
            "⬇ Download PDF Report",
            data=pdf_bytes,
            file_name="rental_agreement_fairness_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with dl_col2:
        st.download_button(
            "⬇ Download Markdown Report",
            data=report_md,
            file_name="rental_agreement_fairness_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl_col3:
        st.download_button(
            "⬇ Download CSV (spreadsheet)",
            data=report_csv,
            file_name="rental_agreement_clauses.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown(f'<div class="rfa-footer">⚖ {result["disclaimer"]}</div>', unsafe_allow_html=True)
if st.button("🔄 Analyze another agreement"):
    del st.session_state["result"]
    st.rerun()
else:
    st.markdown(report_ui.render_empty_state_html(), unsafe_allow_html=True)
