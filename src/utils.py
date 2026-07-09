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


_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22,
    "twenty-three": 23, "twenty-four": 24, "thirty": 30, "forty-five": 45,
    "sixty": 60, "ninety": 90,
}
_WORD_NUMBER_PATTERN = "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True))


def _parse_number_token(token: str) -> float:
    """token is either a digit string or a spelled-out number word (already lowercase)."""
    token = token.strip()
    if token in _WORD_NUMBERS:
        return float(_WORD_NUMBERS[token])
    return float(token)


def extract_number_and_unit(text: str):
    """
    Extract the first numeric quantity + unit from a clause.
    Returns (value: float or None, unit: str or None), where unit is one of
    "percent", "months", "days", or "currency" (a bare rupee amount with no
    explicit months/days unit attached, e.g. "Rs. 1,00,000").

    Handles:
      - digits: "5 months", "90 days", "10%"
      - spelled-out numbers: "twelve months", "one month", "five (5) months"
      - bare currency amounts: "Rs. 1,00,000", "₹50,000", "INR 25000"
    """
    text_lower = text.lower()
    num_token = r"(?:\d+(?:\.\d+)?|" + _WORD_NUMBER_PATTERN + r")"

    # percentages
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text_lower)
    if m:
        return float(m.group(1)), "percent"

    # "X months" / "X-month" / "five (X) months" / "twelve months"
    m = re.search(num_token + r"\s*\)?\s*(?:-|\s)?months?", text_lower)
    if m:
        return _parse_number_token(m.group(0).split()[0].rstrip(")").rstrip("-")), "months"

    # "X days" / "X-day" / "ninety days"
    m = re.search(num_token + r"\s*\)?\s*(?:-|\s)?days?", text_lower)
    if m:
        return _parse_number_token(m.group(0).split()[0].rstrip(")").rstrip("-")), "days"

    # Bare currency amount with no months/days attached, e.g. "Rs. 1,00,000",
    # "₹ 50,000", "INR 25000/-". Digits only (currency amounts are never
    # spelled out in agreements), commas stripped.
    m = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", text_lower)
    if m:
        cleaned = m.group(1).replace(",", "")
        try:
            return float(cleaned), "currency"
        except ValueError:
            pass

    return None, None


def extract_monthly_rent(full_text: str):
    """
    Best-effort scan of the *whole* cleaned agreement (not a single clause) for
    a stated monthly rent figure, e.g. "monthly rent of Rs. 25,000",
    "rent of Rs. 25,000 per month". Used to convert a deposit stated as a bare
    currency amount into a months-of-rent equivalent for scoring/benchmarking.
    Returns float or None if no confident match is found.
    """
    text_lower = full_text.lower()
    patterns = [
        r"monthly rent[^₹\d]{0,45}(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)",
        r"rent[^₹\d]{0,20}(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(?:per month|/-\s*per month|p\.?m\.?)",
        r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(?:per month|/-\s*per month|p\.?m\.?)\s*(?:as|towards)?\s*rent",
    ]
    for pattern in patterns:
        m = re.search(pattern, text_lower)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))
