"""
test_scoring.py
Validates the risk-scoring engine against the hand-labeled evaluation set
(data/labeled_eval_set.csv). Computes accuracy and prints a per-category
breakdown -- this is the "evaluation/validation" deliverable required by the
project brief (Day 6).

Run with:  pytest tests/test_scoring.py -v -s
"""
import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils import Clause
from src.classifier import classify_clause
from src.risk_scoring import score_clause

EVAL_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "labeled_eval_set.csv")


def _load_eval_rows():
    with open(EVAL_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_classifier_matches_expected_category():
    rows = _load_eval_rows()
    correct = 0
    for row in rows:
        clause = Clause(clause_id="test", original_text=row["clause_text"])
        clause = classify_clause(clause)
        if clause.category == row["category"]:
            correct += 1
    accuracy = correct / len(rows)
    print(f"\nClassifier accuracy: {accuracy:.2%} ({correct}/{len(rows)})")
    assert accuracy >= 0.85, "Classifier accuracy dropped below acceptable threshold"


def test_risk_scoring_matches_expected_level():
    rows = _load_eval_rows()
    correct = 0
    mismatches = []
    for row in rows:
        clause = Clause(clause_id="test", original_text=row["clause_text"], category=row["category"])
        result = score_clause(clause)
        if result["risk_level"] == row["expected_risk"]:
            correct += 1
        else:
            mismatches.append((row["clause_text"][:60], row["expected_risk"], result["risk_level"]))

    accuracy = correct / len(rows)
    print(f"\nRisk scoring accuracy: {accuracy:.2%} ({correct}/{len(rows)})")
    if mismatches:
        print("Mismatches (text | expected | got):")
        for text, expected, got in mismatches:
            print(f"  - {text}... | {expected} | {got}")

    assert accuracy >= 0.75, "Risk scoring accuracy dropped below acceptable threshold"


def test_no_missed_red_flags_scored_as_green():
    """A red-flag clause scored as green (false negative) is the worst failure mode."""
    rows = _load_eval_rows()
    dangerous_misses = 0
    for row in rows:
        if row["expected_risk"] != "red":
            continue
        clause = Clause(clause_id="test", original_text=row["clause_text"], category=row["category"])
        result = score_clause(clause)
        if result["risk_level"] == "green":
            dangerous_misses += 1

    assert dangerous_misses == 0, f"{dangerous_misses} red-flag clause(s) were scored as green (false negative)"


def test_fairness_score_ranks_agreements_correctly():
    """A clearly fair agreement should score higher than a clearly predatory one."""
    from src.fairness_score import compute_fairness_score
    from src.main import process_agreement

    fair = process_agreement(file_path="data/sample_agreement_1.txt", log_result=False)
    predatory = process_agreement(file_path="data/sample_agreement_3.txt", log_result=False)

    fair_score = fair["fairness_score"]["score"]
    predatory_score = predatory["fairness_score"]["score"]

    print(f"\nFairness score -- fair agreement: {fair_score}, predatory agreement: {predatory_score}")
    assert fair_score > predatory_score, "Fairness score failed to rank the fair agreement above the predatory one"
    assert fair["fairness_score"]["grade"] in ("A", "B")
    assert predatory["fairness_score"]["grade"] in ("D", "F")


def test_locality_benchmark_flags_above_typical_deposit():
    from src.locality_benchmark import compare_to_locality

    result = compare_to_locality("deposit", 10, "months", "metro_tier1")
    assert result is not None
    assert result["delta_percent"] > 0, "10-month deposit should be flagged as above typical for a metro"


def test_locality_benchmark_rejects_mismatched_units():
    """A day-count must not be compared against a percent-based benchmark (or vice versa)."""
    from src.locality_benchmark import compare_to_locality

    # 15 "days" found inside a rent_increase clause must NOT be compared against
    # the rent_increase_percent typical value -- that would be comparing days to percent.
    result = compare_to_locality("rent_increase", 15, "days", "metro_tier1")
    assert result is None, "Mismatched unit (days) should not produce a rent_increase percent comparison"


def test_audio_summary_is_clean_and_mentions_key_facts():
    """The spoken summary should be plain text (no markdown/brackets) and reflect the score."""
    from src.main import process_agreement

    result = process_agreement(file_path="data/sample_agreement_3.txt", log_result=False)
    summary = result["audio_summary"]

    print(f"\nAudio summary sample (predatory agreement): {summary[:120]}...")

    assert "[" not in summary and "]" not in summary, "Audio summary should not contain bracket labels"
    assert "--" not in summary, "Audio summary should not contain raw em-dashes"
    assert str(result["fairness_score"]["score"]) in summary, "Audio summary should state the fairness score"
    assert "not legal advice" in summary.lower(), "Audio summary must include the responsible-use disclaimer"


if __name__ == "__main__":
    test_classifier_matches_expected_category()
    test_risk_scoring_matches_expected_level()
    test_no_missed_red_flags_scored_as_green()
    test_fairness_score_ranks_agreements_correctly()
    test_locality_benchmark_flags_above_typical_deposit()
    test_locality_benchmark_rejects_mismatched_units()
    test_audio_summary_is_clean_and_mentions_key_facts()
    print("\nAll tests passed.")
