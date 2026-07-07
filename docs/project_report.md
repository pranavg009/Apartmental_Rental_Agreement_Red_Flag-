# Project Report: Apartment Rental Agreement Red Flag Agent

## 1. Real-World Impact

Rental agreements are dense, legally-worded documents most tenants sign under time pressure
without reading every clause. Clauses around deposits, notice periods, lock-in terms, and
maintenance liability are where disputes most commonly arise later. This agent gives tenants a
fast, structured first read of an agreement — flagging what's unusual and explaining why —
while explicitly staying out of the business of giving legal advice or making the decision for
the tenant.

## 2. Stakeholders

| Stakeholder | Need | How the agent serves them |
|---|---|---|
| Tenant | Understand risk before signing | Plain-English clause explanations + risk labels |
| Tenant | Know what to do next | Negotiation Coach: ready-to-send messages |
| Landlord/broker | Faster, clearer negotiation | Specific, well-reasoned points of discussion |
| Legal advisor | Tool stays in scope | Guardrails refuse legal-advice questions |

## 3. System Architecture (as built)

```
Input (PDF / DOCX / TXT / pasted text)
        │
        ▼
┌────────────────────┐
│ ingestion.py        │  Loads raw text (pdfplumber / python-docx / plain read)
└─────────┬───────────┘
          ▼
┌────────────────────┐
│ preprocessing.py    │  Cleans whitespace, segments into clauses via numbered
└─────────┬───────────┘  headings (falls back to paragraph splitting)
          ▼
┌────────────────────┐
│ classifier.py       │  Weighted keyword matching → 8-category taxonomy
└─────────┬───────────┘
          ▼
┌────────────────────┐     ┌──────────────────────────┐
│ retrieval.py         │◄──│ data/reference_norms.json │  Typical/caution/red thresholds
└─────────┬───────────┘     └──────────────────────────┘
          ▼
┌────────────────────┐
│ risk_scoring.py     │  Numeric threshold rules + hard red-flag phrase detection
└─────────┬───────────┘
          ▼
┌────────────────────┐
│ guardrails.py       │  Confidence-threshold review flag + explanation sanitization
└─────────┬───────────┘
          ▼
┌──────────┬──────────────────┬─────────────────┐
▼                              ▼                  ▼
explainer.py            negotiation_coach.py    heatmap.py
(plain English)          (unique feature #2)    (unique feature #1)
          │                    │                  │
          ▼                    ▼                  ▼
┌────────────────────────────────────────────────┐
│ main.py — orchestrates the above into one report │
└─────────┬────────────────────────────────────────┘
          ▼
┌────────────────────┐    ┌────────────────────┐
│ app/app.py          │    │ logger.py            │
│ (Streamlit UI)       │    │ (SQLite run/feedback)│
└────────────────────┘    └────────────────────┘
```

## 4. Why Rule-Based First, LLM-Optional

The base pipeline (classification, scoring, explanation, negotiation messages) is fully
rule-based and runs with **zero API key**, which was a deliberate design choice:

- **Determinism & explainability** — every risk label traces back to a specific numeric
  threshold or phrase match, which is important in a domain where a wrong "this is fine" could
  cost a tenant money.
- **No cost/availability dependency** — the prototype is fully runnable and testable offline.
- **Clean upgrade path** — every module (`classifier.py`, `risk_scoring.py`, `explainer.py`,
  `negotiation_coach.py`) exposes a parallel `*_with_llm(...)` function with the same
  responsibility, so an LLM can be layered in for messier/unstructured agreements without
  restructuring the pipeline.

## 5. The Five Unique Features (Innovation Component)

### 5.1 Visual Heatmap (`src/heatmap.py`)
Rather than only presenting a table of flagged clauses, the agent renders the **original
agreement text** with each clause inline-highlighted green/yellow/red. This is a deliberate
UX choice: seeing risk *in context*, in the actual sentence the tenant will read, is far more
useful and demo-friendly than an abstract JSON table. The module is also written with a
documented extension path to OCR bounding-box highlighting directly on scanned PDF page
images, for a future version.

### 5.2 Negotiation Coach (`src/negotiation_coach.py`)
For every flagged clause, the agent generates a ready-to-send message the tenant can use to
raise the issue with the landlord — e.g. for an unusually long lock-in period, it drafts:
*"Could we discuss the lock-in terms? ... I'd like to understand if there's flexibility for
early exit with reasonable notice instead of full forfeiture."* This directly satisfies the
brief's requirement that the tool "help the user understand what action to take next," rather
than stopping at detection.

### 5.3 Agreement Fairness Score (`src/fairness_score.py`)
All per-clause flags are aggregated into a single 0–100 score and A–F letter grade for the
whole agreement — a "credit score for your rental agreement." The scoring is intentionally
transparent rather than a black box: every clause starts at a perfect baseline, red flags
subtract the most, yellow flags subtract a little, and each penalty is scaled by the flag's own
confidence so uncertain assessments don't unfairly tank the score. This gives the tenant one
memorable headline number to complement the clause-by-clause detail, and validates cleanly:
the fair sample scores 100/A, the mixed sample 46/D, and the predatory sample 0/F.

### 5.4 Locality-Aware Benchmarking (`src/locality_benchmark.py`)
When the tenant selects their city tier, every numeric clause (deposit months, notice days,
lock-in months, rent-increase %) is compared against `data/locality_norms.json` typical values
for that tier, producing concrete comparisons like *"66.7% higher than typical for Tier-1
Metro (typical: 3 months)."* This adds a regional, data-driven dimension beyond the fixed
global thresholds in `reference_norms.json`, and makes the "why is this flagged" reasoning
more concrete for the tenant.

### 5.5 Voice / Accessibility Mode (`src/accessibility.py`)
The agent generates a clean, spoken-friendly narrative summary of the whole agreement — leading
with the fairness score and grade, then walking through red flags, then a brief mention of
caution items, and closing with the responsible-use disclaimer — plus a per-clause spoken line.
The Streamlit UI wires this to a "🔊 Read Aloud" control built on the browser's native Web
Speech API (`speechSynthesis`), so no server-side TTS engine, audio file generation, or API key
is required. Text is deliberately scrubbed of markdown, brackets, and em-dashes before being
spoken, since those read out awkwardly through synthesized voices. This turns the tool from a
read-only interface into something usable by elderly or visually impaired tenants, directly
supporting the brief's emphasis on real-world housing literacy access, not just correctness.

## 6. Dashboard Design & Professionalization

The Streamlit UI (`app/app.py`) is built on a dedicated design system (`src/report_ui.py`) with
an "official assessment report" identity, rather than default Streamlit styling — chosen because
the product's subject matter (a legal-adjacent document review) benefits from looking like a
credible report, not a generic data dashboard. Five specific passes were applied, each addressing
a common way dashboards read as unfinished:

1. **One visual signature, not five.** The circular Fairness Seal (a conic-gradient progress
   ring with a dashed inner border, echoing an official certification stamp) is the single bold
   element. Every other component — clause cards, the risk bar, badges, buttons — is deliberately
   quiet and shares the same restrained palette, so the seal reads as an intentional focal point
   rather than one of several competing effects.
2. **A color system that means something, used everywhere.** The same red/amber/green hex values
   appear in the seal ring, the risk bar, every clause badge, the heatmap, *and* the PDF export.
   This surfaced a real inconsistency during testing — `heatmap.py` originally used a different,
   unrelated color set than the rest of the app — which was caught and fixed as part of this pass.
3. **A distinct typeface for data vs. prose.** IBM Plex Mono (monospace) is reserved specifically
   for anything measured — the fairness score, risk-bar counts, per-clause confidence percentage,
   regional-comparison figures — while Source Serif 4 handles headlines and Inter handles body
   text. Numbers are typeset to visually read as data, not decoration.
4. **Downloadable, portable results.** A PDF report (`src/pdf_report.py`, via `reportlab`,
   matching the same visual identity), a Markdown report, and a CSV export (one row per clause)
   are all one click away, so the assessment can be shared with a landlord, family member, or
   advisor outside the browser tab, not just viewed in-session.
5. **Designed empty and loading states.** The empty state previews the four things the report
   will contain, instead of a bare "upload something" prompt. Analysis runs through `st.status`
   driven by a real `progress_callback` hook threaded through `main.py` (reading → segmenting →
   classifying → scoring → building the heatmap → computing the score → logging) — genuine
   pipeline stages surfaced to the user, not a simulated delay.

Because `report_ui.py` has zero dependency on Streamlit itself, every HTML snippet it produces
is unit-tested directly (`tests/test_report_ui.py`) — including HTML tag balance, correct
grade-to-color mapping, risk-bar percentages summing to 100%, and escaping of HTML special
characters — without needing Streamlit installed. The PDF export (`src/pdf_report.py`) has its
own equivalent test file (`tests/test_pdf_report.py`), which reads generated PDFs back with
`pypdf` to confirm the fairness score, grade, and every clause ID actually appear in the output,
not just that a valid PDF was produced.

## 7. Guardrails & Responsible Use

1. **No legal-advice phrasing** — `guardrails.sanitize_explanation()` strips prescriptive
   phrases like "you should sign" or "this is illegal" if they ever appear in generated text.
2. **Legal-advice question refusal** — `guardrails.guard_user_query()` detects and refuses
   questions like "should I sue my landlord?" with a redirect to a qualified professional.
3. **Confidence-based human review** — any flag scored below a 0.45 confidence threshold is
   marked `needs_human_review: true` rather than presented as a confident verdict.
4. **Standing disclaimer** — every report includes a disclaimer that the tool is not legal
   advice and may not reflect local tenancy law.

## 8. Evaluation Methodology & Results

A 21-row hand-labeled evaluation set (`data/labeled_eval_set.csv`) was built covering all 8
clause categories across green/yellow/red risk levels. `tests/test_scoring.py` checks:

| Metric | Result | Threshold |
|---|---|---|
| Clause classification accuracy | 90.5% (19/21) | ≥85% |
| Risk-level scoring accuracy | 76.2% (16/21) | ≥75% |
| Dangerous false negatives (red scored as green) | 0 | 0 required |

**Interpretation:** The agent is highly reliable at the extremes (clearly fair vs. clearly
predatory clauses) and never silently clears a genuinely red-flag clause as safe. Most scoring
misses were the middle "yellow/caution" band, which is inherently subjective even for human
reviewers — the agent tends to round up to "red" rather than under-flag, which is the safer
failure mode for this use case.

## 9. Sample Run Results

| Agreement | Red | Yellow | Green | Fairness Score |
|---|---|---|---|---|
| sample_agreement_1.txt (fair) | 0 | 0 | 8 | 100 / A |
| sample_agreement_2.txt (mixed) | 4 | 3 | 1 | 46 / D |
| sample_agreement_3.txt (predatory) | 7 | 1 | 0 | 0 / F |

This spread confirms the scoring engine — both at the clause level and the aggregate Fairness
Score — responds proportionally to how predatory the input agreement actually is, rather than
flattening everything to the same output.

## 10. Limitations (Responsible-Use Notes)

- Reference thresholds (`reference_norms.json`) are general norms, not sourced from any single
  jurisdiction's binding tenancy law.
- Clause segmentation depends on numbered headings; unusual formatting may under-segment.
- The tool never gives legal advice or tells a tenant what to legally do — by design, not
  as a missing feature.
- Middle-band ("yellow") risk classification is the least precise part of the system and
  should be read as "worth a second look," not a confident verdict.

## 11. Future Improvements

1. OCR bounding-box heatmap on scanned PDF images (extension already scoped in `heatmap.py`).
2. LLM-backed classification/scoring for unstructured agreements (hooks already defined).
3. Expand the reference knowledge base with cited, state-specific tenancy rules.
4. Downloadable MP3 export of the audio summary via a server-side TTS library, for offline
   listening beyond the current browser-based Web Speech API.
