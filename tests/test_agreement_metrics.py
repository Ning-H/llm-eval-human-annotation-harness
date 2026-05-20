from __future__ import annotations

import pandas as pd

from eval.agreement_metrics import cohen_kappa_by_axis, pairwise_exact_agreement


def test_pairwise_exact_agreement_uses_latest_two_scores():
    events = pd.DataFrame(
        [
            {"response_id": "r1", "axis": "helpfulness", "score": 4, "created_at": "2026-01-01"},
            {"response_id": "r1", "axis": "helpfulness", "score": 4, "created_at": "2026-01-02"},
            {"response_id": "r2", "axis": "helpfulness", "score": 2, "created_at": "2026-01-01"},
            {"response_id": "r2", "axis": "helpfulness", "score": 4, "created_at": "2026-01-02"},
        ]
    )

    result = pairwise_exact_agreement(events)

    assert result.loc[0, "comparison_count"] == 2
    assert result.loc[0, "exact_agreement"] == 0.5


def test_cohen_kappa_returns_axis_rows_for_sparse_data():
    events = pd.DataFrame(
        [
            {"response_id": "r1", "axis": "harm", "score": 4, "created_at": "2026-01-01"},
            {"response_id": "r1", "axis": "harm", "score": 3, "created_at": "2026-01-02"},
            {"response_id": "r2", "axis": "harm", "score": 2, "created_at": "2026-01-01"},
            {"response_id": "r2", "axis": "harm", "score": 2, "created_at": "2026-01-02"},
        ]
    )

    result = cohen_kappa_by_axis(events)

    assert result["axis"].tolist() == ["harm"]
    assert result.loc[0, "item_count"] == 2
