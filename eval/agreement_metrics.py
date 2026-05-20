from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

try:
    import krippendorff
except ImportError:  # pragma: no cover
    krippendorff = None


def pairwise_exact_agreement(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["axis", "comparison_count", "exact_agreement"])

    rows = []
    for axis, axis_df in events.dropna(subset=["score"]).groupby("axis"):
        comparisons = []
        for _, group in axis_df.groupby("response_id"):
            scores = group.sort_values("created_at")["score"].tolist()
            if len(scores) >= 2:
                comparisons.append(scores[-1] == scores[-2])
        rows.append(
            {
                "axis": axis,
                "comparison_count": len(comparisons),
                "exact_agreement": float(np.mean(comparisons)) if comparisons else np.nan,
            }
        )
    return pd.DataFrame(rows)


def cohen_kappa_by_axis(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["axis", "item_count", "cohen_kappa"])

    rows = []
    for axis, axis_df in events.dropna(subset=["score"]).groupby("axis"):
        first_scores = []
        second_scores = []
        for _, group in axis_df.groupby("response_id"):
            scores = group.sort_values("created_at")["score"].tolist()
            if len(scores) >= 2:
                first_scores.append(scores[-2])
                second_scores.append(scores[-1])
        if len(first_scores) < 2 or len(set(first_scores + second_scores)) < 2:
            kappa = np.nan
        else:
            kappa = cohen_kappa_score(first_scores, second_scores, labels=[1, 2, 3, 4])
        rows.append({"axis": axis, "item_count": len(first_scores), "cohen_kappa": kappa})
    return pd.DataFrame(rows)


def ordinal_krippendorff_alpha(events: pd.DataFrame) -> float:
    if events.empty or krippendorff is None:
        return np.nan

    scored = events.dropna(subset=["score"]).copy()
    if scored.empty:
        return np.nan

    scored["rating_idx"] = scored.groupby(["response_id", "axis"]).cumcount()
    scored["unit"] = scored["response_id"].astype(str) + "::" + scored["axis"].astype(str)
    matrix = scored.pivot_table(index="rating_idx", columns="unit", values="score", aggfunc="last")
    if matrix.shape[0] < 2 or matrix.shape[1] < 2:
        return np.nan
    return float(
        krippendorff.alpha(
            reliability_data=matrix.to_numpy(),
            level_of_measurement="ordinal",
        )
    )


def score_correlation(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for axis, axis_df in events.dropna(subset=["score"]).groupby("axis"):
        first_scores = []
        second_scores = []
        for _, group in axis_df.groupby("response_id"):
            scores = group.sort_values("created_at")["score"].tolist()
            if len(scores) >= 2:
                first_scores.append(scores[-2])
                second_scores.append(scores[-1])
        if len(first_scores) < 2:
            corr = np.nan
        else:
            corr = pd.Series(first_scores).corr(pd.Series(second_scores), method="spearman")
        rows.append({"axis": axis, "item_count": len(first_scores), "spearman": corr})
    return pd.DataFrame(rows)
