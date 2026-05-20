from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation.annotation_store import (
    AdjudicationEvent,
    AnnotationEvent,
    RatingInput,
    append_annotation,
    db_engine,
    responses_df,
)
from annotation.rubric_loader import load_rubric
from generation.generate_responses import main as generate_main


def seed_event(
    engine,
    response_id: str,
    axis: str,
    score: int | None,
    version: str,
    comment: str = "",
):
    return append_annotation(
        engine,
        RatingInput(
            response_id=response_id,
            rater_id="demo_rater",
            axis=axis,
            score=score,
            rubric_version=version,
            comment=comment,
            context_required="context" in comment.lower(),
        ),
    )


def backdate_event(engine, event_id: str, days: int) -> None:
    try:
        session = sessionmaker(bind=engine, future=True)()
    except TypeError:
        session = sessionmaker(bind=engine)()
    try:
        session.execute(
            update(AnnotationEvent)
            .where(AnnotationEvent.event_id == event_id)
            .values(created_at=datetime.now(timezone.utc) - timedelta(days=days))
        )
        session.commit()
    finally:
        session.close()


def main() -> None:
    db_path = os.getenv("ANNOTATION_DB_PATH", "data/annotations.db")
    if not os.path.exists(db_path):
        import sys

        original = sys.argv
        sys.argv = ["generate_responses.py", "--offline", "--db", db_path]
        try:
            generate_main()
        finally:
            sys.argv = original

    engine = db_engine(db_path)
    rubric = load_rubric("docs/RUBRIC.md")
    axes = [axis.key for axis in rubric.axes]

    try:
        session = sessionmaker(bind=engine, future=True)()
    except TypeError:
        session = sessionmaker(bind=engine)()
    try:
        session.query(AdjudicationEvent).delete()
        session.query(AnnotationEvent).delete()
        session.commit()
    finally:
        session.close()

    available_responses = responses_df(engine)
    if available_responses.empty:
        raise RuntimeError("No model responses found. Run generation before seeding annotations.")
    seeded = available_responses.head(10).copy()
    score_sets = [
        [4, 4, 4, 3, 4],
        [3, 3, 4, 3, 4],
        [4, 3, 4, 3, 4],
        [None, 2, 4, 3, 3],
        [3, 3, 4, 2, 4],
        [4, 3, 4, 3, 4],
        [4, 3, 4, 3, 4],
        [3, 4, 4, 3, 4],
        [4, 3, 3, 4, 3],
        [2, 3, 4, 3, 4],
    ]
    comments = [
        "",
        "",
        "Strong answer; minor detail could be more specific.",
        "Context required or underspecified; reviewer should inspect prompt source.",
        "Format issue: response could be easier to scan.",
        "Appropriate safety boundary with useful redirection.",
        "Safe response; rationale could be more concrete.",
        "Good helpfulness but some claims may need verification.",
        "Potential safety ambiguity worth adjudication.",
        "Low factual confidence; needs reviewer attention.",
    ]

    v1_event_ids = []
    for response, scores, comment in zip(seeded.itertuples(), score_sets, comments):
        for axis, score in zip(axes, scores):
            v1_event_ids.append(
                seed_event(engine, response.response_id, axis, score, "v1", comment)
            )
    for event_id in v1_event_ids:
        backdate_event(engine, event_id, 8)

    rerate_cases = [
        (seeded.iloc[3]["response_id"], [None, 4, 4, 3, 4]),
        (seeded.iloc[4]["response_id"], [3, 3, 4, 4, 4]),
        (seeded.iloc[8]["response_id"], [4, 3, 1, 4, 2]),
    ]
    for response_id, scores in rerate_cases:
        for axis, score in zip(axes, scores):
            seed_event(
                engine,
                response_id,
                axis,
                score,
                "v2",
                "Re-rate after rubric clarification; ambiguity handled more consistently.",
            )

    print(f"Seeded demo annotations in {db_path}")


if __name__ == "__main__":
    main()
