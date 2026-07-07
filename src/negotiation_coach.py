"""
negotiation_coach.py
UNIQUE FEATURE: "Help me negotiate this" -- converts a flagged clause into a
ready-to-send message the tenant can use to raise the issue with the landlord.
This is what turns the agent from a passive *detector* into an actionable
assistant, directly addressing the brief's requirement to help the user
decide what to do next.

Template-based by default (zero API key needed); optional LLM upgrade path
included for more natural phrasing.
"""

_TEMPLATES = {
    "deposit": (
        "Could we revisit the security deposit amount? {reason} "
        "Would you be open to bringing it closer to the typical 2-3 months' rent, "
        "or splitting it into two installments?"
    ),
    "notice_period": (
        "I'd like to align the notice period so it's fair for both sides. {reason} "
        "Could we set the same notice period for both landlord and tenant?"
    ),
    "lock_in": (
        "Could we discuss the lock-in terms? {reason} "
        "I'd like to understand if there's flexibility for early exit with reasonable notice "
        "instead of full forfeiture."
    ),
    "rent_increase": (
        "Could we agree on a fixed, capped annual rent increase in writing? {reason} "
        "That way both of us know what to expect at renewal."
    ),
    "painting_charges": (
        "Could painting charges be based on the actual condition of the walls at move-out, "
        "rather than a fixed deduction? {reason}"
    ),
    "maintenance": (
        "Could we clarify who covers structural vs. day-to-day maintenance in writing? {reason}"
    ),
    "termination": (
        "Could we add a clause requiring written notice and due process before any termination "
        "or entry to the property? {reason}"
    ),
    "utilities": (
        "Could utility charges be billed based on actual meter readings with itemized bills, "
        "rather than a flat undocumented amount? {reason}"
    ),
    "other": (
        "Could you help me understand this clause better before I sign? {reason}"
    ),
}


def suggest_negotiation_message(category: str, reason: str) -> str:
    """Return a ready-to-send negotiation message for a flagged clause."""
    template = _TEMPLATES.get(category, _TEMPLATES["other"])
    return template.format(reason=reason)


def suggest_with_llm(clause_text: str, category: str, reason: str, call_llm_fn) -> str:
    """Optional upgrade path for a more personalized negotiation message via LLM."""
    prompt = (
        "Write a short, polite message (2-3 sentences) a tenant could send their landlord "
        "to renegotiate the following clause. Be constructive, not confrontational. "
        "Do not give legal advice or threats.\n\n"
        f"Clause category: {category}\nWhy it's flagged: {reason}\nClause text: {clause_text}"
    )
    return call_llm_fn(prompt).strip()
