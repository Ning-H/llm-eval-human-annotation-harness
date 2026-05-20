from __future__ import annotations

import pandas as pd

from annotation.disagreement_detector import review_reasons


def format_recent_scores(values: pd.Series) -> str:
    return ", ".join("N/A" if pd.isna(value) else str(int(value)) for value in values.tail(3))


def join_comments(values: pd.Series) -> str:
    return " | ".join(value for value in values.dropna().astype(str) if value)


def latest_annotation_summary(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(
            columns=[
                "response_id",
                "axis",
                "latest_scores",
                "min_score",
                "max_score",
                "rating_count",
                "comments",
            ]
        )
    scored = events.copy()
    scored["created_at"] = pd.to_datetime(scored["created_at"])
    scored = scored.sort_values("created_at")
    grouped = scored.groupby(["response_id", "axis"], dropna=False)
    return grouped.agg(
        latest_scores=("score", format_recent_scores),
        min_score=("score", "min"),
        max_score=("score", "max"),
        rating_count=("event_id", "count"),
        comments=("comment", join_comments),
    ).reset_index()


def adjudication_queue(
    responses: pd.DataFrame,
    events: pd.DataFrame,
    adjudications: pd.DataFrame,
) -> pd.DataFrame:
    reasons = review_reasons(events)
    if reasons.empty:
        return pd.DataFrame(
            columns=[
                "response_id",
                "axis",
                "reason",
                "severity",
                "category",
                "model_provider",
                "model_name",
                "prompt_text",
                "response_text",
            ]
        )

    resolved_pairs = set()
    if not adjudications.empty:
        resolved_pairs = set(zip(adjudications["response_id"], adjudications["axis"]))

    queue = reasons[
        ~reasons.apply(lambda row: (row["response_id"], row["axis"]) in resolved_pairs, axis=1)
    ].merge(responses, on="response_id", how="left")
    summary = latest_annotation_summary(events)
    queue = queue.merge(summary, on=["response_id", "axis"], how="left")
    severity_order = {"high": 0, "medium": 1, "low": 2}
    queue["severity_rank"] = queue["severity"].map(severity_order).fillna(99)
    return queue.sort_values(["severity_rank", "category", "response_id", "axis"]).drop(
        columns=["severity_rank"]
    )
