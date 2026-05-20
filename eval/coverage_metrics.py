from __future__ import annotations

import pandas as pd


def response_axis_coverage(
    responses: pd.DataFrame, events: pd.DataFrame, expected_axes: list[str]
) -> pd.DataFrame:
    if responses.empty:
        return pd.DataFrame(columns=["response_id", "rated_axes", "coverage"])
    rated = (
        events.drop_duplicates(["response_id", "axis"])
        .groupby("response_id")["axis"]
        .nunique()
        .rename("rated_axes")
    )
    coverage = responses[["response_id", "model_provider", "category"]].drop_duplicates().merge(
        rated, on="response_id", how="left"
    )
    coverage["rated_axes"] = coverage["rated_axes"].fillna(0).astype(int)
    coverage["coverage"] = coverage["rated_axes"] / max(len(expected_axes), 1)
    return coverage


def category_coverage(
    responses: pd.DataFrame, events: pd.DataFrame, expected_axes: list[str]
) -> pd.DataFrame:
    coverage = response_axis_coverage(responses, events, expected_axes)
    if coverage.empty:
        return pd.DataFrame(columns=["category", "response_count", "mean_coverage"])
    return (
        coverage.groupby("category")
        .agg(response_count=("response_id", "count"), mean_coverage=("coverage", "mean"))
        .reset_index()
    )


def axis_coverage(events: pd.DataFrame, expected_axes: list[str]) -> pd.DataFrame:
    total_responses = events["response_id"].nunique() if not events.empty else 0
    rows = []
    for axis in expected_axes:
        rated_responses = (
            events.loc[events["axis"] == axis, "response_id"].nunique() if not events.empty else 0
        )
        rows.append(
            {
                "axis": axis,
                "rated_responses": rated_responses,
                "coverage": rated_responses / total_responses if total_responses else 0.0,
            }
        )
    return pd.DataFrame(rows)
