from __future__ import annotations

import pandas as pd

from annotation.disagreement_detector import detect_disagreements


def test_detect_disagreements_flags_two_point_delta():
    events = pd.DataFrame(
        [
            {"response_id": "r1", "axis": "factuality", "score": 4, "created_at": "2026-01-01"},
            {"response_id": "r1", "axis": "factuality", "score": 2, "created_at": "2026-01-02"},
            {"response_id": "r2", "axis": "factuality", "score": 3, "created_at": "2026-01-01"},
            {"response_id": "r2", "axis": "factuality", "score": 4, "created_at": "2026-01-02"},
        ]
    )

    flags = detect_disagreements(events)

    assert flags["response_id"].tolist() == ["r1"]
    assert flags.iloc[0]["delta"] == 2
