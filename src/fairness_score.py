"""
fairness_score.py
UNIQUE FEATURE #4: Agreement Fairness Score.

Aggregates all per-clause risk flags into a single 0-100 score and letter
grade for the whole agreement -- a "credit score for your rental agreement."
This gives the tenant one memorable headline number in addition to the
clause-by-clause detail, which is both genuinely useful (quick gut-check
before reading further) and demo-friendly (a single gauge/number to show).

Scoring is deliberately simple and transparent (not a black box): every
clause starts the agreement at a perfect baseline, red flags subtract the
most, yellow flags subtract a little, and confidence dampens the penalty
for low-confidence flags so uncertain clauses don't unfairly tank the score.
"""
from dataclasses import dataclass

_RED_PENALTY = 18
_YELLOW_PENALTY = 6
_GREEN_BONUS = 0  # green clauses simply don't penalize; no need to reward further

_GRADE_THRESHOLDS = [
    (85, "A", "Excellent -- this agreement largely follows fair, standard practice."),
    (70, "B", "Good -- a few points worth clarifying, but nothing alarming overall."),
    (50, "C", "Mixed -- several clauses deserve a closer look before signing."),
    (30, "D", "Concerning -- multiple red-flag clauses; strongly recommend review."),
    (0, "F", "High risk -- this agreement has significant one-sided or predatory terms."),
]


@dataclass
class FairnessScore:
    score: int
    grade: str
    summary: str
    red_count: int
    yellow_count: int
    green_count: int


def compute_fairness_score(flags: list[dict]) -> FairnessScore:
    """Aggregate per-clause flags into a single agreement-level fairness score."""
    if not flags:
        return FairnessScore(score=100, grade="A", summary="No clauses to assess.", red_count=0, yellow_count=0, green_count=0)

    score = 100.0
    red_count = yellow_count = green_count = 0

    for flag in flags:
        confidence = flag.get("confidence", 0.5)
        level = flag.get("risk_level")
        if level == "red":
            red_count += 1
            score -= _RED_PENALTY * confidence
        elif level == "yellow":
            yellow_count += 1
            score -= _YELLOW_PENALTY * confidence
        elif level == "green":
            green_count += 1
            score += _GREEN_BONUS

    score = max(0, min(100, round(score)))

    grade, summary = "F", ""
    for threshold, letter, description in _GRADE_THRESHOLDS:
        if score >= threshold:
            grade, summary = letter, description
            break

    return FairnessScore(
        score=score,
        grade=grade,
        summary=summary,
        red_count=red_count,
        yellow_count=yellow_count,
        green_count=green_count,
    )
