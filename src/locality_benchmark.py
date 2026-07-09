"""
locality_benchmark.py
UNIQUE FEATURE #3: Locality-Aware Benchmarking.

Compares a clause's numeric term (deposit months, notice days, lock-in months,
rent-increase %) against typical values for the tenant's selected city tier,
producing a concrete, data-driven comparison such as:
  "Your deposit is 67% higher than typical for Tier-1 metros."

This adds a regional, data-driven dimension on top of the fixed reference
thresholds in reference_norms.json, and is a natural conversation starter for
a demo ("select your city, see how your agreement compares").
"""
import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "locality_norms.json")

_cache = None

# Maps clause category -> the field name in locality_norms.json
_CATEGORY_FIELD_MAP = {
    "deposit": "deposit_months",
    "notice_period": "notice_days",
    "lock_in": "lock_in_months",
    "rent_increase": "rent_increase_percent",
}

# The unit that extract_number_and_unit() must have found for the comparison to be
# semantically valid -- e.g. a "15 days" figure inside a rent_increase clause (referring
# to a notice period mentioned in the same sentence) must NOT be compared against the
# rent_increase_percent benchmark just because it's the first number found in the text.
_CATEGORY_EXPECTED_UNIT = {
    "deposit": "months",
    "notice_period": "days",
    "lock_in": "months",
    "rent_increase": "percent",
}


def _load_locality_norms(path: str = _DEFAULT_PATH) -> dict:
    global _cache
    if _cache is None:
        with open(path, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def list_city_tiers(path: str = _DEFAULT_PATH) -> dict:
    """Returns {tier_key: label} for populating a UI dropdown."""
    norms = _load_locality_norms(path)
    return {k: v["label"] for k, v in norms.items() if not k.startswith("_")}


def compare_to_locality(category: str, value: float, unit: str, city_tier: str, path: str = _DEFAULT_PATH) -> dict | None:
    """
    Compare a clause's extracted numeric value against the typical value for a
    given city tier. Returns None if the category isn't benchmarkable, the
    city tier is unknown, or the extracted unit doesn't match what this
    category benchmarks (e.g. a day-count found inside a rent_increase clause
    must not be compared against the rent-increase percent threshold).

    Returns: {"typical_value": float, "delta_percent": float, "comparison_text": str}
    """
    field = _CATEGORY_FIELD_MAP.get(category)
    expected_unit = _CATEGORY_EXPECTED_UNIT.get(category)
    if field is None or value is None or unit != expected_unit:
        return None

    norms = _load_locality_norms(path)
    tier_data = norms.get(city_tier)
    if tier_data is None or field not in tier_data:
        return None

    typical_value = tier_data[field]
    if typical_value == 0:
        return None

    delta_percent = round(((value - typical_value) / typical_value) * 100, 1)

    if abs(delta_percent) < 10:
        comparison_text = f"In line with the typical value for {tier_data['label']} ({typical_value})."
    elif delta_percent > 0:
        comparison_text = (
            f"{delta_percent}% higher than typical for {tier_data['label']} "
            f"(typical: {typical_value})."
        )
    else:
        comparison_text = (
            f"{abs(delta_percent)}% lower than typical for {tier_data['label']} "
            f"(typical: {typical_value})."
        )

    return {
        "typical_value": typical_value,
        "delta_percent": delta_percent,
        "comparison_text": comparison_text,
    }


# Multipliers applied to a tier's typical value to derive caution/red-flag
# thresholds for that region, so "compare to your region" changes the actual
# verdict (not just a caption). Calibrated from this project's own fixed
# reference_norms.json ratios (e.g. deposit: caution=6 is 2x the generic
# typical_max=3, red=8 is ~2.67x) rather than picked arbitrarily -- so a
# Tier-1 selection reproduces today's generic thresholds almost exactly,
# while Tier-2/3 (which have lower typical values) become correspondingly
# stricter.
_TIER_THRESHOLD_MULTIPLIERS = {
    "deposit": {"caution": 2.0, "red": 2.67},
    "notice_period": {"caution": 2.0, "red": 3.0},
    "lock_in": {"caution": 1.83, "red": 3.0},
    "rent_increase": {"caution": 2.0},
}


def get_tier_relative_thresholds(category: str, city_tier: str, path: str = _DEFAULT_PATH) -> dict | None:
    """
    Derive caution/red thresholds for `category` from the selected tier's
    typical value. Returns {"caution": float, "red": float | None} or None
    if this category isn't tier-benchmarkable or the tier is unknown.
    """
    field = _CATEGORY_FIELD_MAP.get(category)
    multipliers = _TIER_THRESHOLD_MULTIPLIERS.get(category)
    if field is None or multipliers is None or not city_tier:
        return None

    norms = _load_locality_norms(path)
    tier_data = norms.get(city_tier)
    if tier_data is None or field not in tier_data:
        return None

    typical_value = tier_data[field]
    if not typical_value:
        return None

    return {
        "caution": round(typical_value * multipliers["caution"], 2),
        "red": round(typical_value * multipliers["red"], 2) if "red" in multipliers else None,
    }
