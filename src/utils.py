"""
utils.py
Shared data schemas and small helpers used across the pipeline.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional
import re


VALID_CATEGORIES = [
    "deposit",
    "notice_period",
    "lock_in",
    "rent_increase",
    "painting_charges",
    "maintenance",
    "termination",
    "utilities",
    "other",
]

VALID_RISK_LEVELS = ["green", "yellow", "red"]


@dataclass
class Clause:
    clause_id: str
    original_text: str
    category: str = "other"
    start_char: int = 0
    end_char: int = 0


@dataclass
class RiskFlag:
    clause_id: str
    category: str
    original_text: str
    risk_level: str
    confidence: float
    reason: str
    explanation: str
    suggested_question_to_landlord: Optional[str] = None
    needs_human_review: bool = False

    def to_dict(self):
        return asdict(self)


def extract_number_and_unit(text: str):
    """
    Extract the first numeric quantity + unit (months/days/percent) from a clause.
    Returns (value: float or None, unit: str or None)
    Handles both digits ('5 months') and spelled-out numbers in parentheses ('five (5) months').
    """
    text_lower = text.lower()

    # percentages
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text_lower)
    if m:
        return float(m.group(1)), "percent"

    # "X months" / "X-month" / "five (X) months" — allow an optional closing paren
    # and extra spacing between the digit and the unit word.
    m = re.search(r"(\d+(?:\.\d+)?)\s*\)?\s*(?:-|\s)?months?", text_lower)
    if m:
        return float(m.group(1)), "months"

    # "X days" / "X-day"
    m = re.search(r"(\d+(?:\.\d+)?)\s*\)?\s*(?:-|\s)?days?", text_lower)
    if m:
        return float(m.group(1)), "days"

    return None, None


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))
