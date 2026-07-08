"""
classifier.py
Categorizes each clause into a fixed taxonomy.

Default: fast, free, offline keyword-based classifier (no API key needed).
Optional: swap in an LLM call (see classify_with_llm) for messier/unstructured
agreements where keyword matching is insufficient. This keeps the base
pipeline runnable without any API key, while leaving a clean upgrade path.
"""
from src.utils import Clause, VALID_CATEGORIES

_KEYWORDS = {
    "painting_charges": ["painting", "paint charges", "repaint"],
    "lock_in": ["lock-in", "lock in", "lockin"],
    "rent_increase": [
        "rent increase", "increase the rent", "increase rent", "increased by",
        "rent shall be increased", "hike", "escalation", "revision of rent",
    ],
    "notice_period": ["notice period", "notice of", "days' notice", "days notice", "written notice"],
    "termination": ["terminat", "repossess", "evict", "enter the premises"],
    "maintenance": ["maintenance", "repair", "upkeep"],
    "utilities": ["utilit", "electricity", "water charges", "water bill"],
    "deposit": ["deposit", "security amount", "advance amount"],
}


def classify_clause(clause: Clause) -> Clause:
    """
    Assign a category using weighted keyword matching. Each keyword occurrence
    contributes a weight equal to its word count (multi-word phrases like
    "increase rent" are stronger, more specific signals than a single common
    word), summed per category, with the highest-scoring category winning.
    Ties are broken by dict order (more specific categories listed first),
    e.g. "painting_charges" before "deposit" so a clause mentioning painting
    deductions from the deposit is still classified as painting_charges.
    """
    text_lower = clause.original_text.lower()

    best_category = "other"
    best_score = 0.0
    for category, keywords in _KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            occurrences = text_lower.count(kw)
            if occurrences:
                score += occurrences * len(kw.split())
        if score > best_score:
            best_score = score
            best_category = category

    clause.category = best_category if best_score > 0 else "other"
    return clause


def classify_clauses(clauses: list[Clause]) -> list[Clause]:
    return [classify_clause(c) for c in clauses]


def classify_with_llm(clause_text: str, call_llm_fn) -> str:
    """
    Optional upgrade path: classify an ambiguous clause using an LLM.
    `call_llm_fn` should be a function(prompt: str) -> str, e.g. a thin wrapper
    around the Anthropic API. Kept separate so the base pipeline has zero
    hard dependency on an API key.
    """
    prompt = (
        "Classify the following rental-agreement clause into exactly one of these "
        f"categories: {', '.join(VALID_CATEGORIES)}.\n"
        "Respond with only the category name, nothing else.\n\n"
        f"Clause:\n{clause_text}"
    )
    response = call_llm_fn(prompt).strip().lower()
    return response if response in VALID_CATEGORIES else "other"

def upgrade_low_confidence_with_llm(clauses: list[Clause]) -> list[Clause]:
    """
    Re-classify only the clauses the keyword matcher couldn't confidently
    place (category == "other"), using the LLM. Leaves confidently-matched
    clauses untouched to keep cost/latency low.
    """
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return clauses  # no key configured -> silently keep keyword-only results

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    def call_llm(prompt: str) -> str:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    for clause in clauses:
        if clause.category == "other":
            clause.category = classify_with_llm(clause.original_text, call_llm)
    return clauses
