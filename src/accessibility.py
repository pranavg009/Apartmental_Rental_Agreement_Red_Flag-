"""
accessibility.py
UNIQUE FEATURE #5: Voice / Accessibility Mode.

Generates a plain-language, spoken-friendly narrative summary of the whole
agreement (fairness score + each flagged clause), designed to be read aloud
via text-to-speech. This makes the tool usable for elderly or visually
impaired tenants, and for anyone who'd rather listen than read a wall of text.

Deliberately avoids markdown, emoji, symbols, and redundant category labels
in the output text, since those get read out awkwardly ("bracket Rent
Increase bracket") or repeated twice by most speech synthesis engines --
everything here is written as clean, short sentences.
"""
import re

_RISK_SPOKEN = {"red": "a red flag", "yellow": "worth a closer look", "green": "looking fine"}


def generate_audio_summary(flags: list[dict], fairness: dict, max_clauses: int = 6) -> str:
    """
    Build a short, TTS-friendly narrative summary.
    Leads with the headline fairness score, then walks through red flags first
    (most important), then a brief mention of caution items, capped at
    max_clauses spoken in detail to keep the audio summary a reasonable length.
    """
    sentences = []

    sentences.append(
        f"This agreement scores {fairness['score']} out of 100, which is a grade "
        f"{fairness['grade']}. {_strip_for_speech(fairness['summary'])}"
    )

    red_flags = [f for f in flags if f["risk_level"] == "red"]
    yellow_flags = [f for f in flags if f["risk_level"] == "yellow"]

    if red_flags:
        sentences.append(
            f"There are {len(red_flags)} red flag clause"
            f"{'s' if len(red_flags) != 1 else ''} that need your attention."
        )
        for f in red_flags[:max_clauses]:
            label = f["category"].replace("_", " ")
            sentences.append(f"On {label}: {_strip_for_speech(f['explanation'])}")
        remaining = len(red_flags) - max_clauses
        if remaining > 0:
            sentences.append(
                f"There {'is' if remaining == 1 else 'are'} {remaining} more red flag "
                f"clause{'s' if remaining != 1 else ''} detailed in the full report."
            )
    else:
        sentences.append("There are no red flag clauses in this agreement.")

    if yellow_flags:
        sentences.append(
            f"There are also {len(yellow_flags)} clause"
            f"{'s' if len(yellow_flags) != 1 else ''} worth a second look, "
            "including " + _list_categories(yellow_flags) + "."
        )

    sentences.append(
        "Remember, this is not legal advice. For anything flagged red, consider "
        "talking to a local tenant rights group or a qualified lawyer before you sign."
    )

    return " ".join(sentences)


def generate_clause_audio_text(category: str, risk_level: str, explanation: str) -> str:
    """Build a short spoken line for a single clause (used by a per-clause 'listen' button)."""
    label = category.replace("_", " ")
    spoken_risk = _RISK_SPOKEN.get(risk_level, risk_level)
    return f"{label}. This clause is {spoken_risk}. {_strip_for_speech(explanation)}"


def _strip_for_speech(text: str) -> str:
    """
    Clean an explanation string for speech synthesis:
    - remove a leading "[Category Label]" prefix (the audio narration already
      states the category separately, so this avoids saying it twice)
    - replace em-dashes with commas for a natural pause instead of a symbol
    - collapse extra whitespace left behind by the above
    """
    cleaned = re.sub(r"^\[[^\]]+\]\s*", "", text)
    cleaned = cleaned.replace("--", ",")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    return cleaned.strip()


def _list_categories(flags: list[dict]) -> str:
    labels = [f["category"].replace("_", " ") for f in flags]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + ", and " + labels[-1]
