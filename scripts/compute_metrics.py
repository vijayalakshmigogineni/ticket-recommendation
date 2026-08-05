"""Compute reliability metrics for the LLM Decision layer from recorded
manager feedback (recommendation_feedback table) -- accuracy/precision/
recall/F1 on the binary should_attach call, a confusion matrix, and a simple
confidence-calibration check.

This does NOT measure retrieval quality (Recall@K/MRR on whether the correct
ticket even reached the candidate/reranked lists) -- that needs the
per-stage pipeline trace, not the final-decision feedback log, and isn't
computed here. See docs discussion / dashboard conversation for that gap.

Usage: python scripts/compute_metrics.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommender.db import SessionLocal  # noqa: E402
from recommender.models import ManagerDecision, RecommendationFeedback  # noqa: E402


def main() -> None:
    session = SessionLocal()
    try:
        rows = session.query(RecommendationFeedback).all()
    finally:
        session.close()

    total = len(rows)
    if total == 0:
        print("No feedback recorded yet -- accept/reject some recommendations in the "
              "Playground first (see docs/... or ask for test-case suggestions).")
        return

    # should_attach=True is the system's positive class ("this belongs to ticket X").
    # manager_decision=accepted means the manager agrees with whatever the system said
    # (match or no-match); rejected means they disagree.
    tp = fp = tn = fn = 0
    confidences_correct: list[float] = []
    confidences_incorrect: list[float] = []

    for r in rows:
        agreed = r.manager_decision == ManagerDecision.ACCEPTED
        if r.should_attach and agreed:
            tp += 1
        elif r.should_attach and not agreed:
            fp += 1
        elif not r.should_attach and agreed:
            tn += 1
        else:
            fn += 1

        (confidences_correct if agreed else confidences_incorrect).append(r.confidence)

    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) and precision == precision and recall == recall and (precision + recall) > 0
        else float("nan")
    )

    def avg(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else float("nan")

    print(f"Feedback records: {total}\n")

    print("Confusion matrix (should_attach vs. manager verdict):")
    print(f"  True Positive  (attached, manager agreed):      {tp}")
    print(f"  False Positive (attached, manager rejected):     {fp}")
    print(f"  True Negative  (no-match, manager agreed):       {tn}")
    print(f"  False Negative (no-match, manager said it should have matched): {fn}\n")

    print(f"Accuracy:  {accuracy:.3f}")
    print(f"Precision: {precision:.3f}" if precision == precision else "Precision: n/a (no positive predictions)")
    print(f"Recall:    {recall:.3f}" if recall == recall else "Recall: n/a (no actual positives)")
    print(f"F1:        {f1:.3f}" if f1 == f1 else "F1: n/a\n")

    print("\nConfidence calibration (is the system's stated confidence trustworthy?):")
    print(f"  Avg confidence when manager agreed:   {avg(confidences_correct):.3f} "
          f"(n={len(confidences_correct)})")
    print(f"  Avg confidence when manager disagreed: {avg(confidences_incorrect):.3f} "
          f"(n={len(confidences_incorrect)})")
    if confidences_correct and confidences_incorrect and avg(confidences_correct) <= avg(confidences_incorrect):
        print("  WARNING: confidence is not higher on correct calls than incorrect ones -- "
              "the confidence score isn't currently a reliable signal of correctness.")

    if fn > 0:
        rejected_with_correction = [
            r for r in rows
            if r.manager_decision == ManagerDecision.REJECTED and r.corrected_ticket_id is not None
        ]
        print(f"\n{len(rejected_with_correction)} of {fn} false negatives have a manager-supplied "
              "correct ticket -- these are your highest-value cases to inspect first.")


if __name__ == "__main__":
    main()
