"""
main.py
Orchestrates the full pipeline: ingestion -> preprocessing -> classification ->
risk scoring -> explanation -> negotiation coaching -> guardrails -> logging.

This is the single entry point both the CLI and the Streamlit app call into,
so there is exactly one place that defines "how the agent works."
"""
from src import ingestion, preprocessing, classifier, risk_scoring, explainer
from src import negotiation_coach, guardrails, logger, heatmap
from src import fairness_score as fairness_score_module
from src import locality_benchmark
from src import accessibility
from src.utils import RiskFlag, extract_number_and_unit


def process_agreement(
    file_path: str = None,
    raw_text: str = None,
    log_result: bool = True,
    city_tier: str = None,
    progress_callback=None,
) -> dict:
    """
    Run the full pipeline on either a file path or raw pasted text.

    city_tier: optional key into data/locality_norms.json (e.g. "metro_tier1")
    to enable locality-aware benchmarking on numeric clauses (deposit, notice
    period, lock-in, rent increase).

    progress_callback: optional function(message: str) -> None, called at each
    real pipeline stage (not a simulated delay). Used by the Streamlit UI to
    show genuine progress via st.status rather than a generic spinner; has no
    effect on the return value and defaults to a no-op so existing callers
    (CLI, tests) are unaffected.

    Returns a dict: { clauses_found, flags, heatmap_html, run_id, disclaimer,
                       fairness_score: {score, grade, summary, ...} }
    """
    def report(message: str):
        if progress_callback:
            progress_callback(message)

    if file_path:
        report("Reading the agreement file...")
        text = ingestion.load_text(file_path)
    elif raw_text:
        report("Reading the pasted agreement text...")
        text = ingestion.load_text_from_string(raw_text)
    else:
        raise ValueError("Provide either file_path or raw_text.")

    report("Cleaning text and segmenting into clauses...")
    cleaned = preprocessing.clean_text(text)
    clauses = preprocessing.segment_clauses(cleaned)

    report(f"Classifying {len(clauses)} clause(s)...")
    clauses = classifier.classify_clauses(clauses)
    clauses = classifier.upgrade_low_confidence_with_llm(clauses)

    report("Scoring risk against reference norms...")
    flags = []
    for clause in clauses:
        score = risk_scoring.score_clause(clause)
        score = guardrails.apply_confidence_guardrail(score)

        explanation = explainer.explain_clause(clause.category, score["risk_level"], score["reason"])
        explanation = guardrails.sanitize_explanation(explanation)

        suggestion = negotiation_coach.suggest_negotiation_message(clause.category, score["reason"])

        flag = RiskFlag(
            clause_id=clause.clause_id,
            category=clause.category,
            original_text=clause.original_text,
            risk_level=score["risk_level"],
            confidence=score["confidence"],
            reason=score["reason"],
            explanation=explanation,
            suggested_question_to_landlord=suggestion,
            needs_human_review=score["needs_human_review"],
        ).to_dict()

        # heatmap needs char offsets; attach them without polluting the RiskFlag schema
        flag["start_char"] = clause.start_char
        flag["end_char"] = clause.end_char

        # locality-aware benchmarking (unique feature #3), only where a city_tier
        # was provided and the clause has a benchmarkable numeric value.
        # Both the plain-text comparison (used in the audio summary and the
        # markdown/PDF export) and the raw numeric fields (used by the UI to
        # typeset figures in the data typeface) are stored on the flag.
        if city_tier:
            value, unit = extract_number_and_unit(clause.original_text)
            benchmark = locality_benchmark.compare_to_locality(clause.category, value, unit, city_tier)
        else:
            benchmark = None

        flag["locality_comparison"] = benchmark["comparison_text"] if benchmark else None
        flag["locality_delta_percent"] = benchmark["delta_percent"] if benchmark else None
        flag["locality_typical_value"] = benchmark["typical_value"] if benchmark else None

        # spoken-friendly version of this clause's explanation (unique feature #5)
        flag["audio_text"] = accessibility.generate_clause_audio_text(
            clause.category, score["risk_level"], explanation
        )

        flags.append(flag)

    report("Building the visual heatmap...")
    heatmap_html = heatmap.build_html_heatmap(cleaned, flags)

    report("Computing the Fairness Score...")
    fscore = fairness_score_module.compute_fairness_score(flags)
    fairness_dict = {
        "score": fscore.score,
        "grade": fscore.grade,
        "summary": fscore.summary,
        "red_count": fscore.red_count,
        "yellow_count": fscore.yellow_count,
        "green_count": fscore.green_count,
    }

    report("Preparing the audio summary...")
    audio_summary = accessibility.generate_audio_summary(flags, fairness_dict)

    if log_result:
        report("Logging this run...")
        run_id = logger.log_run(flags)
    else:
        run_id = None

    report("Done.")

    return {
        "clauses_found": len(clauses),
        "flags": flags,
        "heatmap_html": heatmap_html,
        "run_id": run_id,
        "disclaimer": guardrails.DISCLAIMER,
        "fairness_score": fairness_dict,
        "audio_summary": audio_summary,
    }


def answer_user_question(user_query: str) -> str:
    """Guardrail-checked entry point for free-text user questions about the agreement."""
    refusal = guardrails.guard_user_query(user_query)
    if refusal:
        return refusal
    return (
        "I can help explain specific clauses or flag risk levels, but I can't answer "
        "general questions outside the agreement text. Try asking about a specific clause."
    )


if __name__ == "__main__":
    import sys
    import json

    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_agreement_2.txt"
    city_tier = sys.argv[2] if len(sys.argv) > 2 else None
    result = process_agreement(file_path=path, city_tier=city_tier)
    print(json.dumps({k: v for k, v in result.items() if k != "heatmap_html"}, indent=2))
    fs = result["fairness_score"]
    print(f"\n{result['clauses_found']} clauses analyzed. Run ID: {result['run_id']}")
    print(f"Agreement Fairness Score: {fs['score']}/100 (Grade {fs['grade']}) -- {fs['summary']}")
