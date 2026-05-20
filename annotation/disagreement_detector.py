from __future__ import annotations

import pandas as pd


def latest_two_scores(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    scored = events.dropna(subset=["score"]).copy()
    scored["created_at"] = pd.to_datetime(scored["created_at"])
    scored = scored.sort_values("created_at")
    return scored.groupby(["response_id", "axis"], as_index=False).tail(2)


def detect_disagreements(events: pd.DataFrame, threshold: int = 2) -> pd.DataFrame:
    recent = latest_two_scores(events)
    if recent.empty:
        return pd.DataFrame(
            columns=["response_id", "axis", "min_score", "max_score", "delta", "rating_count"]
        )

    grouped = (
        recent.groupby(["response_id", "axis"])["score"]
        .agg(min_score="min", max_score="max", rating_count="count")
        .reset_index()
    )
    grouped["delta"] = grouped["max_score"] - grouped["min_score"]
    return grouped[(grouped["rating_count"] >= 2) & (grouped["delta"] >= threshold)].sort_values(
        ["delta", "response_id"], ascending=[False, True]
    )


def review_reasons(events: pd.DataFrame, threshold: int = 2) -> pd.DataFrame:
    disagreements = detect_disagreements(events, threshold)
    context_flags = (
        events[events.get("context_required", False) == True]  # noqa: E712
        [["response_id", "axis"]]
        .drop_duplicates()
        .assign(reason="context-required", severity="medium")
    )
    if disagreements.empty:
        disagreement_flags = pd.DataFrame(columns=["response_id", "axis", "reason", "severity"])
    else:
        disagreement_flags = disagreements[["response_id", "axis"]].assign(
            reason="score-divergence", severity="high"
        )
    return pd.concat([disagreement_flags, context_flags], ignore_index=True).drop_duplicates()
