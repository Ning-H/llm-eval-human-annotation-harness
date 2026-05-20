from __future__ import annotations

import numpy as np
import pandas as pd


def score_distribution(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["rubric_version", "axis", "score", "count", "share"])
    counts = (
        events.dropna(subset=["score"])
        .groupby(["rubric_version", "axis", "score"])
        .size()
        .rename("count")
        .reset_index()
    )
    totals = counts.groupby(["rubric_version", "axis"])["count"].transform("sum")
    counts["share"] = counts["count"] / totals
    return counts


def rubric_version_drift(events: pd.DataFrame, baseline: str, comparison: str) -> pd.DataFrame:
    dist = score_distribution(events)
    rows = []
    for axis in sorted(dist["axis"].unique()) if not dist.empty else []:
        base = _score_vector(dist, baseline, axis)
        comp = _score_vector(dist, comparison, axis)
        rows.append(
            {
                "axis": axis,
                "baseline_version": baseline,
                "comparison_version": comparison,
                "mean_share_abs_delta": float(np.mean(np.abs(comp - base))),
                "baseline_mean_score": _mean_score(dist, baseline, axis),
                "comparison_mean_score": _mean_score(dist, comparison, axis),
            }
        )
    return pd.DataFrame(rows)


def _score_vector(dist: pd.DataFrame, version: str, axis: str) -> np.ndarray:
    subset = dist[(dist["rubric_version"] == version) & (dist["axis"] == axis)]
    shares = {int(row.score): float(row.share) for row in subset.itertuples()}
    return np.array([shares.get(score, 0.0) for score in [1, 2, 3, 4]])


def _mean_score(dist: pd.DataFrame, version: str, axis: str) -> float:
    subset = dist[(dist["rubric_version"] == version) & (dist["axis"] == axis)]
    if subset.empty:
        return np.nan
    return float((subset["score"] * subset["share"]).sum())
