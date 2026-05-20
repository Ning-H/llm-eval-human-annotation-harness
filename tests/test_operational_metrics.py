from __future__ import annotations

import pandas as pd

from eval.adjudication import adjudication_queue
from eval.dataset_diagnostics import dataset_quality_diagnostics
from eval.reports import launch_readiness_report
from eval.scorecards import model_readiness_scorecard


def test_adjudication_queue_excludes_resolved_pairs():
    responses = pd.DataFrame(
        [
            {
                "response_id": "r1",
                "prompt_id": "p1",
                "category": "safety",
                "model_provider": "openai",
                "model_name": "demo",
                "prompt_text": "Unsafe request",
                "response_text": "No.",
            }
        ]
    )
    events = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "response_id": "r1",
                "axis": "harm",
                "score": 4,
                "comment": "",
                "context_required": False,
                "created_at": "2026-01-01",
            },
            {
                "event_id": "e2",
                "response_id": "r1",
                "axis": "harm",
                "score": 2,
                "comment": "Policy boundary.",
                "context_required": False,
                "created_at": "2026-01-02",
            },
        ]
    )
    adjudications = pd.DataFrame(columns=["response_id", "axis"])

    queue = adjudication_queue(responses, events, adjudications)

    assert len(queue) == 1
    assert queue.loc[0, "reason"] == "score-divergence"

    resolved = pd.DataFrame([{"response_id": "r1", "axis": "harm"}])
    assert adjudication_queue(responses, events, resolved).empty


def test_scorecards_and_reports_are_generated():
    responses = pd.DataFrame(
        [
            {
                "response_id": "r1",
                "prompt_id": "p1",
                "category": "helpfulness",
                "model_provider": "openai",
                "model_name": "demo",
                "prompt_text": "Write a useful answer with clear steps for a customer.",
            }
        ]
    )
    events = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "response_id": "r1",
                "axis": "helpfulness",
                "score": 4,
                "context_required": False,
                "created_at": "2026-01-01",
            },
            {
                "event_id": "e2",
                "response_id": "r1",
                "axis": "harm",
                "score": 4,
                "context_required": False,
                "created_at": "2026-01-01",
            },
        ]
    )
    adjudications = pd.DataFrame(columns=["response_id", "axis"])

    scorecard = model_readiness_scorecard(responses, events)
    diagnostics = dataset_quality_diagnostics(responses, events, ["helpfulness", "harm"])
    report = launch_readiness_report(responses, events, adjudications, ["helpfulness", "harm"])

    assert scorecard.loc[0, "readiness"] == "Ready for limited launch"
    assert "no-diagnostic-issue" in set(diagnostics["issue"])
    assert report["response_count"] == 1
