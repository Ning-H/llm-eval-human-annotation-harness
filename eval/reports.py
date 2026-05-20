from __future__ import annotations

import pandas as pd

from eval.adjudication import adjudication_queue
from eval.dataset_diagnostics import dataset_quality_diagnostics, diagnostic_summary
from eval.scorecards import model_readiness_scorecard


def launch_readiness_report(
    responses: pd.DataFrame,
    events: pd.DataFrame,
    adjudications: pd.DataFrame,
    expected_axes: list[str],
) -> dict:
    queue = adjudication_queue(responses, events, adjudications)
    diagnostics = dataset_quality_diagnostics(responses, events, expected_axes)
    scorecard = model_readiness_scorecard(responses, events)
    return {
        "response_count": int(len(responses)),
        "annotation_event_count": int(len(events)),
        "open_adjudication_count": int(len(queue)),
        "adjudicated_count": int(len(adjudications)),
        "diagnostic_issue_count": int(
            diagnostics[diagnostics["issue"] != "no-diagnostic-issue"]["response_id"].nunique()
        )
        if not diagnostics.empty
        else 0,
        "models": scorecard.to_dict(orient="records"),
        "top_diagnostics": diagnostic_summary(diagnostics).head(5).to_dict(orient="records"),
    }
