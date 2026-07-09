"""
risk_scoring.py
Assigns a risk_level (green/yellow/red) and confidence score to each clause.

Approach: hybrid.
  1. Rule-based numeric threshold checks against data/reference_norms.json
     (deterministic, explainable, no API key needed).
  2. Keyword-based "hard red flag" phrase detection for qualitative clauses
     (e.g. "without notice", "at their discretion", "non-refundable").
  3. Optional LLM reasoning hook (score_with_llm) for ambiguous clauses that
     don't match either rule -- these get needs_human_review=True by default
     so the system never silently guesses.
"""
from src.utils import Clause, extract_number_and_unit, clamp_confidence
from src.retrieval import get_reference
from src import locality_benchmark

_HARD_RED_PHRASES = [
    "without notice",
    "without prior notice",
    "at their discretion",
    "at its discretion",
    "non-refundable",
    "regardless of",
    "any reason",
    "without cause",
    "without court process",
    "solely by the landlord",
    "no itemized",
    "unconditionally",
    "whether or not",
]

# Categories that don't have a numeric threshold to check (painting, maintenance,
# termination, utilities). For these, absence of red-flag language is itself a
# reasonably confident positive signal, since there's nothing else to measure.
_QUALITATIVE_CATEGORIES = {"painting_charges", "maintenance", "termination", "utilities"}


def score_clause(clause: Clause, monthly_rent: float = None, city_tier: str = None) -> dict:
    """
    Returns a dict with: risk_level, confidence, reason, needs_human_review,
    normalized_value, normalized_unit.

    monthly_rent: optional figure (extracted once from the whole document via
    utils.extract_monthly_rent) used to convert a deposit stated as a bare
    currency amount ("Rs. 1,00,000") into a months-of-rent equivalent, so it
    can be judged against the same thresholds as "3 months' rent". If the
    deposit's unit isn't "currency", or monthly_rent is unknown, this has no
    effect.

    city_tier: optional key into data/locality_norms.json. When provided, the
    caution/red thresholds for deposit, notice_period, lock_in, and
    rent_increase are derived from that tier's typical value instead of the
    generic fixed thresholds -- so selecting a region can change the actual
    verdict, not just a comparison caption. Falls back to the fixed generic
    thresholds when no tier is selected, or the tier has no data for a
    category.

    normalized_value/normalized_unit on the returned dict are the exact
    (possibly converted) figures used to make the decision -- callers (e.g.
    main.py's locality-benchmark step) should reuse these rather than
    re-extracting, so the score and the regional comparison always agree.
    """
    ref = get_reference(clause.category)
    text_lower = clause.original_text.lower()
    value, unit = extract_number_and_unit(clause.original_text)

    def threshold(generic_key: str, generic_default: float, tier_field: str) -> float:
        if city_tier:
            tier_thresholds = locality_benchmark.get_tier_relative_thresholds(clause.category, city_tier)
            if tier_thresholds and tier_thresholds.get(tier_field) is not None:
                return tier_thresholds[tier_field]
        return ref.get(generic_key, generic_default)

    if clause.category == "deposit" and unit == "currency" and value is not None and monthly_rent:
        value = round(value / monthly_rent, 2)
        unit = "months"

    if clause.category == "notice_period" and unit == "months" and value is not None:
        value = round(value * 30, 1)
        unit = "days"

    hard_flag_hits = [p for p in _HARD_RED_PHRASES if p in text_lower]

    # --- Numeric threshold rules per category ---
    if clause.category == "deposit" and unit == "months" and value is not None:
        red_t = threshold("red_flag_above_months", 8, "red")
        caution_t = threshold("caution_above_months", 6, "caution")
        if value >= red_t:
            return _result("red", 0.9, f"Deposit of {value:g} months exceeds the red-flag threshold ({red_t:g} months).", value=value, unit=unit)
        if value >= caution_t:
            return _result("yellow", 0.75, f"Deposit of {value:g} months is above typical (caution threshold: {caution_t:g} months).", value=value, unit=unit)
        return _result("green", 0.8, f"Deposit of {value:g} months is within typical range.", value=value, unit=unit)

    if clause.category == "notice_period" and unit == "days" and value is not None:
        red_t = threshold("red_flag_above_days", 90, "red")
        caution_t = threshold("caution_above_days", 60, "caution")
        if value >= red_t:
            return _result("red", 0.7, f"Notice period of {int(value)} days is unusually long / one-sided (red-flag threshold: {red_t:g} days).", value=value, unit=unit)
        if value >= caution_t:
            return _result("yellow", 0.6, f"Notice period of {int(value)} days is above typical (caution threshold: {caution_t:g} days).", value=value, unit=unit)
        return _result("green", 0.75, f"Notice period of {int(value)} days is within typical range.", value=value, unit=unit)

    if clause.category == "lock_in" and unit == "months" and value is not None:
        red_t = threshold("red_flag_above_months", 18, "red")
        caution_t = threshold("caution_above_months", 11, "caution")
        if value >= red_t:
            return _result("red", 0.85, f"Lock-in period of {int(value)} months is unusually long (red-flag threshold: {red_t:g} months).", value=value, unit=unit)
        if value >= caution_t:
            return _result("yellow", 0.65, f"Lock-in period of {int(value)} months is above typical (caution threshold: {caution_t:g} months).", value=value, unit=unit)
        return _result("green", 0.75, f"Lock-in period of {int(value)} months is within typical range.", value=value, unit=unit)

    if clause.category == "rent_increase" and unit == "percent" and value is not None:
        caution_t = threshold("caution_above_percent", 10, "caution")
        if value >= caution_t:
            return _result("yellow", 0.6, f"Rent increase of {value:g}% is above typical (caution threshold: {caution_t:g}%).", value=value, unit=unit)
        return _result("green", 0.75, f"Rent increase of {value:g}% is within typical range.", value=value, unit=unit)

    # --- Hard qualitative red-flag phrase detection ---
    if hard_flag_hits:
        confidence = clamp_confidence(0.55 + 0.1 * len(hard_flag_hits))
        return _result(
            "red",
            confidence,
            f"Contains concerning phrasing: {', '.join(hard_flag_hits[:3])}.",
            value=value, unit=unit,
        )

    # --- Qualitative categories with no red-flag phrasing: reasonably confident green ---
    if clause.category in _QUALITATIVE_CATEGORIES:
        return _result(
            "green",
            0.65,
            "No concerning language detected; appears to follow standard practice.",
            value=value, unit=unit,
        )

    # --- No numeric match, no hard flag, and category expects a number (deposit,
    # notice_period, lock_in, rent_increase): don't guess, flag for human review ---
    return _result(
        "yellow",
        0.35,
        "No strong numeric or phrase-based signal found; low-confidence assessment.",
        needs_human_review=True,
        value=value, unit=unit,
    )


def _result(risk_level, confidence, reason, needs_human_review=False, value=None, unit=None):
    return {
        "risk_level": risk_level,
        "confidence": clamp_confidence(confidence),
        "reason": reason,
        "needs_human_review": needs_human_review,
        "normalized_value": value,
        "normalized_unit": unit,
    }


def score_with_llm(clause_text: str, reference: dict, call_llm_fn) -> dict:
    """
    Optional upgrade path for ambiguous clauses. `call_llm_fn` is a
    function(prompt) -> str wrapping an LLM API call. Expects the LLM to
    return strict JSON: {"risk_level": ..., "confidence": ..., "reason": ...}
    """
    import json

    prompt = (
        "You are assisting a tenant by assessing ONE clause of a rental agreement. "
        "You are not a lawyer and must not give legal advice -- only flag risk level.\n"
        f"Reference norms for this clause category: {json.dumps(reference)}\n"
        f"Clause: {clause_text}\n\n"
        'Respond ONLY with JSON: {"risk_level": "green|yellow|red", '
        '"confidence": 0.0-1.0, "reason": "short reason"}'
    )
    raw = call_llm_fn(prompt)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"risk_level": "yellow", "confidence": 0.3, "reason": "LLM response unparseable; defaulting to caution."}
