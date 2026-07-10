# Apartment Rental Agreement Red Flag Agent

An AI assistant that reviews rental agreement text, flags clauses worth a closer look
(deposit, notice period, lock-in, rent increase, painting charges, maintenance, termination,
utilities), explains them in plain English, and suggests how to raise them with the landlord —
without ever giving legal advice.

**🔗 Live Demo:** [apartmental-rental-agreement.streamlit.app](https://apartmental-rental-agreement.streamlit.app/)

---

## 1. Problem Statement

Tenants often sign rental agreements without fully understanding clauses around deposit
amounts, notice periods, rent-increase terms, lock-in periods, painting charges, and
maintenance liability. This project builds a working agent that reads agreement text and
produces a structured, risk-ranked, plain-English breakdown — helping a non-lawyer tenant
know what to ask about before signing, while keeping humans in control of any legal decision.

**Users:** Tenants reviewing a rental agreement before signing.
**Success criteria:** Given raw agreement text, the agent returns clause-by-clause risk
labels, explanations, and actionable next steps within seconds.

---

## 2. Dataset / Reference Source

- Three synthetic sample rental agreements (`data/sample_agreement_1.txt` — mostly fair,
  `sample_agreement_2.txt` — mixed, `sample_agreement_3.txt` — heavily predatory), written to
  mirror common Indian rental agreement structure (see
  [IndiaFilings rental agreement format](https://www.indiafilings.com/learn/rental-agreement-format/)
  for reference).
- `data/reference_norms.json` — a small synthetic knowledge base of typical/caution/red-flag
  numeric thresholds (deposit months, notice days, lock-in months, rent-increase %) used to
  ground the risk scoring (RAG-style lookup).
- `data/labeled_eval_set.csv` — 21 hand-labeled clauses with expected category and risk level,
  used to validate the agent (see Section 9).

**All data in this repository is synthetic starter data created for this project.** It is not
sourced from real tenants or real agreements.

---

## 3. Tools Used

Python, Streamlit, `pdfplumber` (PDF parsing), `python-docx` (DOCX parsing), rule-based NLP
(keyword classification + regex numeric extraction), SQLite (run/feedback logging), `pytest`.
No paid API key is required to run the base pipeline — see Section 6 for the optional LLM
upgrade path.

**Dashboard design:** the Streamlit UI (`app/app.py`) follows a dedicated design system in
`src/report_ui.py` — an "official assessment report" identity (ink-navy + paper background,
a serif headline face, and a monospace face reserved for all measured data/scores), themed via
`.streamlit/config.toml`. The presentation layer is a pure-Python module with zero Streamlit
dependency, so its HTML output is unit-tested directly (`tests/test_report_ui.py`) without
needing Streamlit installed.

**Five professionalization passes applied to the dashboard:**
1. **One visual signature, not five** — the circular Fairness Seal is the single bold element;
   everything else (cards, bars, badges, buttons) is deliberately quiet and shares the same
   restrained palette, so the seal reads as intentional rather than one of many competing effects.
2. **A color system that means something, used everywhere** — the same red/amber/green hex
   values appear in the seal ring, the risk bar, every badge, the heatmap, *and* the PDF export,
   with no stray inconsistent colors.
3. **A distinct typeface for data vs. prose** — IBM Plex Mono is reserved for anything measured
   (the score, risk-bar counts, per-clause confidence %, regional-comparison figures), Source
   Serif 4 for headlines, Inter for body text — so numbers visually read as data, not decoration.
4. **Downloadable, portable results** — a PDF report (`src/pdf_report.py`, via `reportlab`,
   matching the same visual identity), a Markdown report, and a CSV export (one row per clause,
   for spreadsheet analysis) can all be exported with one click, so the fairness assessment can
   be shared with a landlord, family member, or advisor outside the browser tab.
5. **Designed empty and loading states** — the empty state previews the four things the report
   will contain (not just a blank "upload something" prompt). Analysis runs through `st.status`
   with messages tied to `main.py`'s actual `progress_callback` hook (reading → segmenting →
   classifying → scoring → building the heatmap → computing the score → logging) — genuine
   pipeline stages, not a simulated delay, so what the user sees is what's actually happening.

**Hero background:** the hero banner includes a subtle animated dotted-wave surface
(`report_ui.render_hero_with_dotted_surface_html()`), adapted from a React/Three.js/shadcn
component into vanilla JS + Three.js-via-CDN so it runs inside a Streamlit
`st.components.v1.html()` iframe without any Node/React toolchain. Recolored to the report's
navy/slate palette, scaled down and slowed down considerably from the original (which was built
for a full-viewport marketing hero) so it stays in the background rather than competing with the
Fairness Seal, confined to the hero band only (never behind the clause report itself), respects
`prefers-reduced-motion`, and fails silently to a flat navy panel if the CDN is unreachable. The
plain, non-animated hero (`render_hero_html()`) is kept in the same module as a zero-JS fallback.

---

## 4. Project Workflow

```
Agreement (PDF/DOCX/TXT/pasted text)
        │
        ▼
Ingestion  →  Cleaning & Clause Segmentation  →  Clause Classification
        │
        ▼
Retrieval (reference_norms.json)  →  Risk Scoring  →  Guardrail Check
        │
        ▼
Plain-English Explanation  +  Negotiation Message  +  Visual Heatmap
        │
        ▼
Structured JSON Output  →  Streamlit UI  →  Logged to SQLite
```

See `docs/project_report.md` for the full architecture diagrams and design rationale.

---

## 5. AI / Agent Component

- **Clause classification:** weighted keyword matching against a fixed taxonomy (deposit,
  notice_period, lock_in, rent_increase, painting_charges, maintenance, termination, utilities).
- **Retrieval-augmented grounding:** each clause's risk score is checked against a reference
  knowledge base of typical/caution/red-flag thresholds, rather than a free-floating LLM guess.
- **Risk scoring:** hybrid rule-based engine — numeric threshold checks (e.g. deposit ≥ 8
  months → red) plus hard-coded red-flag phrase detection (e.g. "without notice",
  "non-refundable", "at their discretion").
- **Guardrails:** legal-advice question refusal, confidence-threshold-based
  `needs_human_review` flagging, and explanation sanitization to strip prescriptive legal
  phrasing.
- **Five unique/out-of-the-box features:**
  1. **Visual Heatmap** (`src/heatmap.py`) — renders the *original agreement text* with
     inline color-coded highlighting (green/yellow/red) per clause, so risk is seen in context,
     not just listed in a table.
  2. **Negotiation Coach** (`src/negotiation_coach.py`) — for every flagged clause, generates a
     ready-to-send message the tenant can use to raise the issue with the landlord, turning the
     tool from a passive detector into an actionable assistant.
  3. **Agreement Fairness Score** (`src/fairness_score.py`) — aggregates every clause's risk
     level and confidence into a single 0–100 score and letter grade (A–F) for the whole
     agreement, like a credit score for your rental agreement. Transparent, additive scoring
     (no black box) so the number is explainable, not just a headline.
  4. **Locality-Aware Benchmarking** (`src/locality_benchmark.py`) — optionally compares a
     clause's numeric term (deposit months, notice days, lock-in months, rent-increase %)
     against typical values for the tenant's city tier (`data/locality_norms.json`), producing
     concrete comparisons like *"66.7% higher than typical for Tier-1 Metro (typical: 3
     months)."*
  5. **Voice / Accessibility Mode** (`src/accessibility.py`) — generates a clean, spoken-friendly
     narrative summary of the whole agreement (and of each individual clause), and the Streamlit
     UI adds a "🔊 Read Aloud" control powered by the browser's built-in Web Speech API — no
     server-side TTS library or API key needed. Makes the tool usable for elderly or visually
     impaired tenants, or anyone who'd rather listen than read.

An optional LLM-upgrade hook is included in `classifier.py`, `risk_scoring.py`,
`explainer.py`, and `negotiation_coach.py` for teams who want to layer an LLM API on top of the
rule-based baseline for messier/unstructured agreements (see Section 6).

---

## 6. How to Run the Project

### Option A — Try the hosted demo (no install required)

👉 **[apartmental-rental-agreement.streamlit.app](https://apartmental-rental-agreement.streamlit.app/)**

Upload a rental agreement (or paste text) directly in the browser — nothing to set up.

### Option B — Run locally

```bash
# 1. Clone the repository
git clone <this-repo-url>
cd Apartmental_Rental_Agreement_Red_Flag

# 2. Install dependencies
pip install -r requirements.txt

# 3a. Run the pipeline from the command line on a sample agreement
python -m src.main data/sample_agreement_2.txt

# 3b. OR launch the Streamlit UI
streamlit run app/app.py

# 4. Run the full test suite
pytest tests/ -v -s
```

Once analyzed, the dashboard offers one-click **PDF** and **Markdown** report downloads
(bottom of the report view), so results can be shared outside the browser.

**Optional LLM upgrade:** the rule-based pipeline runs with zero API key. To layer in an LLM
for ambiguous clauses, set an API key as an environment variable and pass a `call_llm_fn`
wrapper into the `*_with_llm` functions in `classifier.py`, `risk_scoring.py`, `explainer.py`,
and `negotiation_coach.py` — the interfaces are already defined for this.

---

## 7. Demo Screenshots

Live app: **[apartmental-rental-agreement.streamlit.app](https://apartmental-rental-agreement.streamlit.app/)**

See `docs/screenshots/` for static screenshots of the Streamlit UI (clause cards view and the
heatmap view).

---

## 8. Validation / Evaluation Method

`tests/test_scoring.py` runs the classifier and risk-scoring engine against
`data/labeled_eval_set.csv` (21 hand-labeled clauses) and checks:

1. **Classifier accuracy** — category assigned matches the expected category (≥85% required).
2. **Risk-scoring accuracy** — risk level assigned matches the expected label (≥75% required).
3. **Zero dangerous false negatives** — no clause labeled "red" by a human is ever scored
   "green" by the agent (this is treated as the most important test, since a missed red flag
   is worse than a false alarm in this domain).

`tests/test_report_ui.py` separately validates the dashboard's presentation layer (HTML tag
balance, escaping of special characters, correct color-family mapping per grade, risk-bar
percentages summing to 100%) — runs without Streamlit installed, since `report_ui.py` has no
dependency on it.

Current results: **90% classifier accuracy, 76% risk-scoring accuracy, 0 dangerous false
negatives**, all `report_ui` presentation tests passing.

---

## 9. Limitations

- Rule-based scoring is grounded in general norms (`reference_norms.json`), not actual
  state/local tenancy law — thresholds may not apply to every jurisdiction.
- Clause segmentation relies on numbered-heading patterns; unusually formatted agreements may
  segment imperfectly (falls back to paragraph-based splitting).
- The middle "yellow / caution" risk band is inherently subjective; evaluation shows the
  agent is more confident distinguishing clearly-fair from clearly-predatory clauses than
  fine-grained caution calls.
- This tool does **not** provide legal advice and should not be treated as a substitute for
  a qualified lawyer or local tenant-rights body, especially for anything flagged red.
- OCR-based bounding-box highlighting for scanned/image PDFs is documented as a natural
  extension in `src/heatmap.py` but not implemented in this version (the current heatmap
  works on extracted/typed text).
- Voice/Accessibility Mode relies on the browser's built-in Web Speech API; voice quality and
  availability vary by browser (works in Chrome/Edge/Safari; not guaranteed in every
  environment) and requires the app to run in an actual browser tab, not a headless context.
