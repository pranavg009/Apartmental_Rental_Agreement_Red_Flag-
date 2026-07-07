"""
guardrails.py
Responsible-use safeguards for the agent:
  1. Never phrase output as legal advice ("you must/should legally...").
  2. Detect and refuse out-of-scope legal-advice questions from the user.
  3. Mark low-confidence flags as needing human review instead of guessing.
  4. Attach a standing disclaimer to every report.
"""
import re

DISCLAIMER = (
    "This tool highlights clauses that commonly warrant a closer look based on general "
    "norms. It does NOT provide legal advice and may not reflect your local/state tenancy "
    "law. For anything flagged red, or before signing, consider consulting a local "
    "tenant-rights body or a qualified lawyer."
)

_LEGAL_ADVICE_TRIGGERS = [
    r"\bshould i sue\b",
    r"\bcan i sue\b",
    r"\bis this legal\b",
    r"\bis this illegal\b",
    r"\bwhat are my legal rights\b",
    r"\bwill i win in court\b",
    r"\bshould i sign\b",
]

_LEGAL_ADVICE_REFUSAL = (
    "I can't give legal advice or tell you whether to sign or take legal action. "
    "I can, however, explain what a clause says and flag whether it's unusual "
    "compared to common practice. For legal questions, please consult a local "
    "tenant-rights body or a qualified lawyer."
)

CONFIDENCE_REVIEW_THRESHOLD = 0.45


def is_legal_advice_question(user_query: str) -> bool:
    query_lower = user_query.lower()
    return any(re.search(pattern, query_lower) for pattern in _LEGAL_ADVICE_TRIGGERS)


def guard_user_query(user_query: str) -> str | None:
    """Returns a refusal message if the query is out of scope, else None."""
    if is_legal_advice_question(user_query):
        return _LEGAL_ADVICE_REFUSAL
    return None


def apply_confidence_guardrail(flag: dict) -> dict:
    """Force needs_human_review=True whenever confidence is below threshold."""
    if flag.get("confidence", 1.0) < CONFIDENCE_REVIEW_THRESHOLD:
        flag["needs_human_review"] = True
    return flag


def sanitize_explanation(explanation: str) -> str:
    """Strip prescriptive legal-advice phrasing if it slips into generated text."""
    banned_phrases = [
        "you must legally",
        "you should legally",
        "this is illegal",
        "this is legal",
        "you will win",
        "you should sign",
        "you should not sign",
    ]
    sanitized = explanation
    for phrase in banned_phrases:
        if phrase in sanitized.lower():
            sanitized = (
                "This clause differs from common practice and is worth discussing "
                "with the landlord or a tenant-rights professional."
            )
            break
    return sanitized
