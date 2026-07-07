"""
report_ui.py
Presentation layer for the Streamlit dashboard: CSS design system and HTML
snippet builders. Deliberately has ZERO dependency on streamlit itself, so
every function here can be unit-tested in isolation (see tests/test_report_ui.py)
without needing streamlit installed -- app.py just imports these and calls
st.markdown(..., unsafe_allow_html=True) on the results.

Design language: "official assessment report" rather than a generic dashboard --
deep ink-navy structure, a serif headline face, and a monospace face reserved
for anything that is measured data (scores, percentages, clause numbers), so
numbers visually read as data rather than decoration. Risk color (red/amber/
green) is used consistently everywhere -- badges, the seal ring, the heatmap --
because it encodes a real classification, not a decorative accent.
"""
from html import escape

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

INK = "#16233F"
SLATE = "#5B6472"
PAPER = "#F5F6F9"
CARD = "#FFFFFF"
BORDER = "#E3E6EC"

PALETTE = {
    "red": {"strong": "#B3423A", "tint": "#F8E6E4"},
    "amber": {"strong": "#AD7A17", "tint": "#FBEFD9"},
    "green": {"strong": "#2F7D5C", "tint": "#E3F3EC"},
}

RISK_TO_FAMILY = {"red": "red", "yellow": "amber", "green": "green"}
GRADE_TO_FAMILY = {"A": "green", "B": "green", "C": "amber", "D": "red", "F": "red"}

RISK_LABEL = {"red": "RED FLAG", "yellow": "CAUTION", "green": "LOOKS FINE"}


# ---------------------------------------------------------------------------
# Global CSS (inject once via st.markdown(CSS_BLOCK, unsafe_allow_html=True))
# ---------------------------------------------------------------------------

CSS_BLOCK = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');

:root {
  --ink: #16233F; --slate: #5B6472; --paper: #F5F6F9; --card: #FFFFFF; --border: #E3E6EC;
  --red: #B3423A; --red-tint: #F8E6E4;
  --amber: #AD7A17; --amber-tint: #FBEFD9;
  --green: #2F7D5C; --green-tint: #E3F3EC;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--ink); }
p, span, div, label { font-family: 'Inter', sans-serif; }

/* ---- Hero ---- */
.rfa-hero { background: var(--ink); border-radius: 14px; padding: 28px 32px; margin-bottom: 22px; }
.rfa-eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 2.5px;
  color: #9FB0CE; text-transform: uppercase; margin-bottom: 6px; }
.rfa-hero-title { font-family: 'Source Serif 4', serif; font-weight: 700; font-size: 32px;
  color: #FFFFFF; line-height: 1.15; margin: 0 0 6px 0; }
.rfa-hero-sub { font-family: 'Inter', sans-serif; font-size: 14px; color: #C7D1E3; max-width: 640px; }

/* ---- Section headers ---- */
.rfa-section-eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 2px;
  color: var(--slate); text-transform: uppercase; margin: 6px 0 2px 0; }
.rfa-section-title { font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 22px;
  color: var(--ink); margin: 0 0 14px 0; }

/* ---- Sidebar step labels ---- */
.rfa-side-eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 2px;
  color: var(--slate); text-transform: uppercase; margin: 4px 0 2px 0; }
.rfa-side-title { font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 16px;
  color: var(--ink); margin: 0 0 8px 0; }

/* ---- Fairness Seal ---- */
.rfa-seal-wrap { display: flex; justify-content: center; align-items: center; padding: 6px 0; }
.rfa-seal { width: 168px; height: 168px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; position: relative; box-shadow: 0 8px 20px rgba(22,35,63,0.14); }
.rfa-seal::before { content: ""; position: absolute; width: 132px; height: 132px; border-radius: 50%;
  background: var(--card); border: 1px dashed #C7CCD6; }
.rfa-seal-inner { position: relative; z-index: 2; text-align: center; }
.rfa-seal-score { font-family: 'IBM Plex Mono', monospace; font-size: 42px; font-weight: 600;
  color: var(--ink); line-height: 1; }
.rfa-seal-grade { font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 2px;
  margin-top: 5px; font-weight: 600; }
.rfa-seal-label { font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 1.5px;
  color: var(--slate); text-transform: uppercase; text-align: center; margin-top: 8px; }

/* ---- Risk bar ---- */
.rfa-riskbar { display: flex; width: 100%; height: 14px; border-radius: 7px; overflow: hidden;
  border: 1px solid var(--border); }
.rfa-riskbar-seg { height: 100%; }
.rfa-riskbar-legend { display: flex; gap: 18px; margin-top: 9px; font-size: 13px; color: var(--slate); flex-wrap: wrap; }
.rfa-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; }
.rfa-riskbar-legend .rfa-count { font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: var(--ink); }

/* ---- Clause cards ---- */
.rfa-clause-card { background: var(--card); border: 1px solid var(--border); border-left-width: 5px;
  border-radius: 10px; padding: 16px 18px; margin-bottom: 4px; }
.rfa-clause-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.rfa-badge { font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 600; letter-spacing: 1px;
  padding: 3px 9px; border-radius: 5px; }
.rfa-clause-cat { font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 16px; color: var(--ink); }
.rfa-confidence { font-family: 'Inter', sans-serif; font-size: 10.5px; letter-spacing: 0.5px; text-transform: uppercase;
  color: var(--slate); margin-left: auto; white-space: nowrap; }
.rfa-mono-figure { font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: var(--ink); }
.rfa-quote { border-left: 3px solid var(--border); margin: 0 0 10px 0; padding: 4px 0 4px 12px;
  color: var(--slate); font-size: 13.5px; font-style: italic; }
.rfa-explain { font-size: 14px; margin-bottom: 8px; line-height: 1.5; }
.rfa-locality { font-size: 13px; color: var(--ink); background: var(--paper); border-radius: 6px;
  padding: 6px 10px; margin-bottom: 8px; }
.rfa-review-note { font-size: 13px; color: var(--amber); margin-bottom: 8px; }
.rfa-suggest-label { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 1px;
  text-transform: uppercase; color: var(--slate); margin-bottom: 4px; }
.rfa-suggest-box { background: var(--paper); border: 1px solid var(--border); border-radius: 8px;
  padding: 10px 12px; font-size: 13.5px; line-height: 1.5; }
.rfa-stat-chip { font-size: 13px; color: var(--slate); margin-top: 4px; }

/* ---- Empty state ---- */
.rfa-empty { border: 1px dashed #C7CCD6; border-radius: 12px; padding: 40px 24px; text-align: center;
  background: var(--card); }
.rfa-empty-icon { font-size: 30px; margin-bottom: 10px; }
.rfa-empty-title { font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 18px;
  color: var(--ink); margin-bottom: 6px; }
.rfa-empty-body { font-size: 14px; color: var(--slate); max-width: 440px; margin: 0 auto; }
.rfa-empty-features { display: flex; gap: 18px; justify-content: center; margin-top: 26px; flex-wrap: wrap; }
.rfa-empty-feature { width: 140px; }
.rfa-empty-feature-icon { font-size: 19px; margin-bottom: 4px; }
.rfa-empty-feature-title { font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 12.5px;
  color: var(--ink); margin-bottom: 2px; }
.rfa-empty-feature-desc { font-size: 11.5px; color: var(--slate); line-height: 1.35; }

/* ---- Footer ---- */
.rfa-footer { border-top: 1px solid var(--border); margin-top: 26px; padding-top: 12px;
  font-size: 12.5px; color: var(--slate); font-style: italic; }

/* ---- Light-touch native Streamlit overrides ---- */
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--border); }
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button, .stButton > button {
  border-radius: 8px !important; font-weight: 600 !important; }
div[data-testid="stButton"] button[kind="primary"] {
  background: var(--ink) !important; border-color: var(--ink) !important; }
details { border: 1px solid var(--border) !important; border-radius: 10px !important; background: var(--card) !important; }
summary { font-weight: 600 !important; }
.stTabs [data-baseweb="tab"] { font-weight: 600 !important; }
</style>
"""


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def render_hero_html() -> str:
    """Plain hero banner (no animation) -- rendered via st.markdown. Kept as a fast,
    zero-JS fallback; render_hero_with_dotted_surface_html() below is what app.py
    actually uses by default."""
    return (
        '<div class="rfa-hero">'
        '<div class="rfa-eyebrow">Housing Literacy Tool</div>'
        '<div class="rfa-hero-title">Rental Agreement Red Flag Report</div>'
        '<div class="rfa-hero-sub">Upload or paste your agreement to get a clause-by-clause '
        'fairness assessment, in plain English, with suggested next steps.</div>'
        "</div>"
    )


def render_hero_with_dotted_surface_html(height_px: int = 210) -> str:
    """
    Hero banner with an animated dotted-wave-surface background, adapted from a
    React/Three.js/next-themes shadcn component into vanilla JS + Three.js-via-CDN.

    Why this exists as a separate component (not part of CSS_BLOCK / render_hero_html):
    st.markdown(unsafe_allow_html=True) inserts HTML via innerHTML, and browsers
    never execute <script> tags inserted that way -- only st.components.v1.html()
    (a real iframe) actually runs scripts. So the animated version has to be its
    own self-contained document (styles + markup + Three.js + animation script
    all in one string), rendered with st.components.v1.html(..., height=height_px)
    instead of st.markdown(). Text and canvas share one iframe on purpose, so
    ordinary CSS stacking (absolute canvas behind, relative text on top) works
    exactly like a normal web page -- no fragile cross-element Streamlit layout
    tricks required.

    Design choices vs. the original component:
    - Recolored to the report's palette (soft slate-blue dots on the ink-navy
      hero) instead of the original's plain black/white, and no next-themes
      dependency since this app has a single fixed theme.
    - Much smaller grid, lower amplitude, and slower motion than the original
      (which was built for a full-viewport marketing hero) -- this hero band is
      ~200px tall, and the whole point of the Fairness Seal is to be the one
      bold visual moment, so the background stays deliberately subtle rather
      than competing with it.
    - Confined to the hero band only (not `fixed inset-0` across the whole page),
      so it never sits behind or distracts from the clause-by-clause report.
    - Respects `prefers-reduced-motion`: renders a single static frame instead of
      looping if the visitor's OS has that setting on.
    - Fails silently (falls back to a flat navy panel, no console error) if the
      Three.js CDN is blocked or unreachable -- e.g. offline use, strict
      corporate networks, ad-blockers -- since this is decoration, never a
      requirement for reading the report.
    """
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@600&family=Inter:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,700&display=swap');
  html, body {{ margin:0; padding:0; height:100%; background:transparent; overflow:hidden; }}
  .hero-wrap {{ position:relative; width:100%; height:{height_px}px; border-radius:14px;
    background:#16233F; overflow:hidden; box-sizing:border-box; }}
  .hero-canvas-holder {{ position:absolute; inset:0; z-index:0; }}
  .hero-text {{ position:relative; z-index:1; padding:28px 32px; font-family:'Inter',sans-serif;
    box-sizing:border-box; }}
  .hero-eyebrow {{ font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:2.5px;
    color:#9FB0CE; text-transform:uppercase; margin-bottom:6px; }}
  .hero-title {{ font-family:'Source Serif 4',serif; font-weight:700; font-size:32px;
    color:#FFFFFF; line-height:1.15; margin:0 0 6px 0; }}
  .hero-sub {{ font-size:14px; color:#C7D1E3; max-width:640px; }}
</style>
<div class="hero-wrap">
  <div class="hero-canvas-holder" id="rfa-dots"></div>
  <div class="hero-text">
    <div class="hero-eyebrow">Housing Literacy Tool</div>
    <div class="hero-title">Rental Agreement Red Flag Report</div>
    <div class="hero-sub">Upload or paste your agreement to get a clause-by-clause fairness
      assessment, in plain English, with suggested next steps.</div>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/128/three.min.js"></script>
<script>
(function() {{
  var container = document.getElementById('rfa-dots');
  if (!container || typeof THREE === 'undefined') return;

  var SEPARATION = 26, AMOUNTX = 34, AMOUNTY = 9;
  var width = container.clientWidth || 900;
  var height = container.clientHeight || {height_px};

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(55, width / height, 1, 4000);
  camera.position.set(0, 210, 480);
  camera.lookAt(0, 0, 0);

  var renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true }});
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(width, height);
  container.appendChild(renderer.domElement);

  var positions = [];
  var colors = [];
  var dotColor = new THREE.Color(0x9fb0ce);
  for (var ix = 0; ix < AMOUNTX; ix++) {{
    for (var iy = 0; iy < AMOUNTY; iy++) {{
      var x = ix * SEPARATION - (AMOUNTX * SEPARATION) / 2;
      var z = iy * SEPARATION - (AMOUNTY * SEPARATION) / 2;
      positions.push(x, 0, z);
      colors.push(dotColor.r, dotColor.g, dotColor.b);
    }}
  }}

  var geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

  var material = new THREE.PointsMaterial({{
    size: 3, vertexColors: true, transparent: true, opacity: 0.4, sizeAttenuation: true
  }});
  var points = new THREE.Points(geometry, material);
  scene.add(points);

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var count = 0;
  function animate() {{
    requestAnimationFrame(animate);
    var posAttr = geometry.attributes.position;
    var arr = posAttr.array;
    var i = 0;
    for (var ix = 0; ix < AMOUNTX; ix++) {{
      for (var iy = 0; iy < AMOUNTY; iy++) {{
        var idx = i * 3;
        arr[idx + 1] = Math.sin((ix + count) * 0.4) * 7 + Math.sin((iy + count) * 0.6) * 7;
        i++;
      }}
    }}
    posAttr.needsUpdate = true;
    renderer.render(scene, camera);
    count += 0.02;
  }}

  if (reduceMotion) {{
    renderer.render(scene, camera);
  }} else {{
    animate();
  }}

  window.addEventListener('resize', function() {{
    var w = container.clientWidth || width;
    var h = container.clientHeight || height;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }});
}})();
</script>
"""


def render_section_header_html(eyebrow: str, title: str) -> str:
    return (
        f'<div class="rfa-section-eyebrow">{escape(eyebrow)}</div>'
        f'<div class="rfa-section-title">{escape(title)}</div>'
    )


def render_seal_html(score: int, grade: str) -> str:
    family = GRADE_TO_FAMILY.get(grade, "red")
    strong = PALETTE[family]["strong"]
    degrees = round(max(0, min(100, score)) / 100 * 360, 1)
    return (
        '<div class="rfa-seal-wrap">'
        f'<div class="rfa-seal" style="background:conic-gradient({strong} 0deg {degrees}deg, '
        f'#E3E6EC {degrees}deg 360deg);">'
        '<div class="rfa-seal-inner">'
        f'<div class="rfa-seal-score">{int(score)}</div>'
        f'<div class="rfa-seal-grade" style="color:{strong};">GRADE {escape(str(grade))}</div>'
        "</div></div>"
        '<div class="rfa-seal-label">Agreement Fairness Seal</div>'
        "</div>"
    )


def render_risk_bar_html(red: int, yellow: int, green: int) -> str:
    total = max(1, red + yellow + green)
    r_pct, y_pct, g_pct = red / total * 100, yellow / total * 100, green / total * 100
    return (
        '<div class="rfa-riskbar">'
        f'<div class="rfa-riskbar-seg" style="width:{r_pct}%; background:var(--red);"></div>'
        f'<div class="rfa-riskbar-seg" style="width:{y_pct}%; background:var(--amber);"></div>'
        f'<div class="rfa-riskbar-seg" style="width:{g_pct}%; background:var(--green);"></div>'
        "</div>"
        '<div class="rfa-riskbar-legend">'
        f'<span><span class="rfa-dot" style="background:var(--red);"></span>'
        f'<span class="rfa-count">{red}</span> red flag(s)</span>'
        f'<span><span class="rfa-dot" style="background:var(--amber);"></span>'
        f'<span class="rfa-count">{yellow}</span> caution</span>'
        f'<span><span class="rfa-dot" style="background:var(--green);"></span>'
        f'<span class="rfa-count">{green}</span> look fine</span>'
        "</div>"
    )


def render_clause_card_html(flag: dict) -> str:
    family = RISK_TO_FAMILY.get(flag["risk_level"], "amber")
    strong, tint = PALETTE[family]["strong"], PALETTE[family]["tint"]
    risk_label = RISK_LABEL.get(flag["risk_level"], flag["risk_level"].upper())
    category_label = flag["category"].replace("_", " ").title()
    confidence_pct = round(flag.get("confidence", 0) * 100)

    review_html = ""
    if flag.get("needs_human_review"):
        review_html = '<div class="rfa-review-note">⚠ Low confidence — worth a human or legal review.</div>'

    locality_html = _render_locality_line(flag)

    return (
        f'<div class="rfa-clause-card" style="border-left-color:{strong};">'
        '<div class="rfa-clause-head">'
        f'<span class="rfa-badge" style="background:{tint}; color:{strong};">{escape(risk_label)}</span>'
        f'<span class="rfa-clause-cat">{escape(category_label)}</span>'
        f'<span class="rfa-confidence">CONFIDENCE <span class="rfa-mono-figure">{confidence_pct}%</span></span>'
        "</div>"
        f'<blockquote class="rfa-quote">{escape(flag["original_text"])}</blockquote>'
        f'<div class="rfa-explain"><strong>What this means:</strong> {escape(flag["explanation"])}</div>'
        f"{locality_html}{review_html}"
        '<div class="rfa-suggest-label">Suggested message to your landlord</div>'
        f'<div class="rfa-suggest-box">{escape(flag["suggested_question_to_landlord"])}</div>'
        "</div>"
    )


def _render_locality_line(flag: dict) -> str:
    """
    Build the regional-comparison line. Prefers the structured numeric fields
    (locality_delta_percent / locality_typical_value) so figures can be wrapped
    in the mono data typeface directly -- safer than regex-searching the
    pre-formatted comparison_text string for numbers (which risks mangling
    HTML entities produced by escaping). Falls back to the plain-text
    comparison if the numeric fields aren't present for any reason.
    """
    comparison_text = flag.get("locality_comparison")
    if not comparison_text:
        return ""

    delta = flag.get("locality_delta_percent")
    typical = flag.get("locality_typical_value")
    if delta is None or typical is None:
        return f'<div class="rfa-locality">📍 {escape(comparison_text)}</div>'

    typical_str = f"{typical:g}"
    if abs(delta) < 10:
        body = f'In line with the typical value for your region (<span class="rfa-mono-figure">{typical_str}</span>).'
    else:
        direction = "higher" if delta > 0 else "lower"
        body = (
            f'<span class="rfa-mono-figure">{abs(delta):g}%</span> {direction} than typical for your region '
            f'(typical: <span class="rfa-mono-figure">{typical_str}</span>).'
        )
    return f'<div class="rfa-locality">📍 {body}</div>'


def render_empty_state_html() -> str:
    features = [
        ("🎯", "Fairness Score", "One score and grade for the whole agreement"),
        ("📋", "Clause-by-clause", "Plain-English risk explanation for every clause"),
        ("🖍️", "Visual Heatmap", "Risk highlighted directly on your agreement text"),
        ("💬", "Negotiation Coach", "Ready-to-send messages for anything flagged"),
    ]
    features_html = "".join(
        '<div class="rfa-empty-feature">'
        f'<div class="rfa-empty-feature-icon">{icon}</div>'
        f'<div class="rfa-empty-feature-title">{escape(title)}</div>'
        f'<div class="rfa-empty-feature-desc">{escape(desc)}</div>'
        "</div>"
        for icon, title, desc in features
    )
    return (
        '<div class="rfa-empty">'
        '<div class="rfa-empty-icon">📑</div>'
        '<div class="rfa-empty-title">No agreement analyzed yet</div>'
        '<div class="rfa-empty-body">Upload a file, paste your agreement text, or try a sample from the '
        "left panel, then select <strong>Analyze Agreement</strong> to generate your fairness report.</div>"
        f'<div class="rfa-empty-features">{features_html}</div>'
        "</div>"
    )


def render_clause_count_html(count: int) -> str:
    return f'<div class="rfa-stat-chip"><span class="rfa-mono-figure">{int(count)}</span> clauses analyzed</div>'


# ---------------------------------------------------------------------------
# Downloadable report (plain Markdown, no extra dependency)
# ---------------------------------------------------------------------------

def build_markdown_report(result: dict, city_tier_label: str = None) -> str:
    fs = result["fairness_score"]
    lines = [
        "# Rental Agreement Fairness Report",
        "",
        f"**Fairness Score:** {fs['score']}/100 (Grade {fs['grade']})  ",
        f"**Summary:** {fs['summary']}  ",
        f"**Breakdown:** {fs['red_count']} red flag(s), {fs['yellow_count']} caution, "
        f"{fs['green_count']} look fine, out of {result['clauses_found']} clauses analyzed.",
    ]
    if city_tier_label:
        lines.append(f"**Benchmarked against:** {city_tier_label}")
    lines += ["", "---", ""]

    ordering = {"red": 0, "yellow": 1, "green": 2}
    for f in sorted(result["flags"], key=lambda x: ordering[x["risk_level"]]):
        lines.append(f"## {f['clause_id']} — {f['category'].replace('_', ' ').title()} — {f['risk_level'].upper()}")
        lines.append("")
        lines.append(f"> {f['original_text']}")
        lines.append("")
        lines.append(f"**What this means:** {f['explanation']}")
        if f.get("locality_comparison"):
            lines.append("")
            lines.append(f"**Regional comparison:** {f['locality_comparison']}")
        if f.get("needs_human_review"):
            lines.append("")
            lines.append("_Low confidence — recommend a human/legal review of this clause._")
        lines.append("")
        lines.append(f"**Suggested message to your landlord:** {f['suggested_question_to_landlord']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"*{result['disclaimer']}*")
    return "\n".join(lines)


def build_csv_report(result: dict) -> str:
    """CSV export of every clause's data, for anyone who wants to work with it in a spreadsheet."""
    import io
    import csv

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "clause_id", "category", "risk_level", "confidence", "reason",
        "explanation", "locality_comparison", "needs_human_review",
        "suggested_question_to_landlord",
    ])
    ordering = {"red": 0, "yellow": 1, "green": 2}
    for f in sorted(result["flags"], key=lambda x: ordering[x["risk_level"]]):
        writer.writerow([
            f["clause_id"], f["category"], f["risk_level"], f["confidence"], f["reason"],
            f["explanation"], f.get("locality_comparison") or "", f["needs_human_review"],
            f["suggested_question_to_landlord"],
        ])
    return buffer.getvalue()
