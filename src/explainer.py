"""
explainer.py
Converts a clause + risk assessment into a plain-English explanation a
non-lawyer tenant can understand. Template-based by default (works with
zero API key); can be swapped for an LLM call for richer phrasing.
"""

_CATEGORY_LABELS = {
    "deposit": "Security Deposit",
    "notice_period": "Notice Period",
    "lock_in": "Lock-in Period",
    "rent_increase": "Rent Increase",
    "painting_charges": "Painting Charges",
    "maintenance": "Maintenance Responsibility",
    "termination": "Termination Terms",
    "utilities": "Utility Charges",
    "other": "General Clause",
}

_RISK_INTRO = {
    "green": "This looks in line with common practice.",
    "yellow": "This is worth a closer look before you sign.",
    "red": "This clause could work against you -- treat it as a priority to discuss.",
}


def explain_clause(category: str, risk_level: str, reason: str) -> str:
    """Build a plain-English explanation for a scored clause."""
    label = _CATEGORY_LABELS.get(category, "Clause")
    intro = _RISK_INTRO.get(risk_level, "")
    return f"[{label}] {intro} {reason}".strip()


def explain_with_llm(clause_text: str, category: str, risk_level: str, reason: str, call_llm_fn) -> str:
    """
    Optional upgrade path: use an LLM to generate a more natural explanation.
    Prompt is written to avoid legal-advice phrasing.
    """
    prompt = (
        "Explain the following rental clause to a tenant in 2-3 simple sentences. "
        "Do not give legal advice or tell them what to legally do -- only explain "
        "what the clause means and why it might matter.\n\n"
        f"Category: {category}\nRisk level: {risk_level}\nInternal reason: {reason}\n"
        f"Clause text: {clause_text}"
    )
    return call_llm_fn(prompt).strip()
