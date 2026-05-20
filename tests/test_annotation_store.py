from __future__ import annotations

from annotation.annotation_store import (
    AdjudicationInput,
    RatingInput,
    adjudications_df,
    annotations_df,
    append_adjudication,
    append_annotation,
    create_engine_for_tests,
    init_annotation_db,
)


def test_append_annotation_preserves_multiple_events():
    engine = create_engine_for_tests()
    init_annotation_db(engine)

    first = append_annotation(
        engine,
        RatingInput(
            response_id="r1",
            rater_id="demo",
            axis="helpfulness",
            score=4,
            rubric_version="v1",
        ),
    )
    second = append_annotation(
        engine,
        RatingInput(
            response_id="r1",
            rater_id="demo",
            axis="helpfulness",
            score=2,
            rubric_version="v2",
            comment="Changed interpretation after rubric clarification.",
        ),
    )

    events = annotations_df(engine)

    assert first != second
    assert len(events) == 2
    assert events["rubric_version"].tolist() == ["v1", "v2"]


def test_append_adjudication_records_final_decision():
    engine = create_engine_for_tests()
    init_annotation_db(engine)

    adjudication_id = append_adjudication(
        engine,
        AdjudicationInput(
            response_id="r1",
            axis="refusal_appropriateness",
            adjudicator_id="lead",
            final_score=4,
            resolution_type="rubric-ambiguity",
            rationale="The refusal was appropriate under the clarified policy.",
            rubric_version="v2",
        ),
    )

    adjudications = adjudications_df(engine)

    assert len(adjudications) == 1
    assert adjudications.loc[0, "adjudication_id"] == adjudication_id
    assert adjudications.loc[0, "final_score"] == 4
