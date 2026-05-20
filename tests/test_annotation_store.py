from __future__ import annotations

from annotation.annotation_store import (
    RatingInput,
    annotations_df,
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
