from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

try:
    from sqlalchemy.orm import declarative_base
except ImportError:  # SQLAlchemy < 1.4
    from sqlalchemy.ext.declarative import declarative_base

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from generation.response_store import Base as ResponseBase
from generation.response_store import get_engine, init_response_db

AnnotationBase = declarative_base(metadata=MetaData())


class AnnotationEvent(AnnotationBase):
    __tablename__ = "annotation_events"

    event_id = Column(String, primary_key=True)
    response_id = Column(String, nullable=False, index=True)
    rater_id = Column(String, nullable=False, index=True)
    axis = Column(String, nullable=False, index=True)
    score = Column(Integer, nullable=True)
    rubric_version = Column(String, nullable=False, index=True)
    comment = Column(Text, nullable=True)
    context_required = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ReviewFlag(AnnotationBase):
    __tablename__ = "review_flags"

    flag_id = Column(String, primary_key=True)
    response_id = Column(String, nullable=False, index=True)
    reason = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), nullable=False)


class AdjudicationEvent(AnnotationBase):
    __tablename__ = "adjudication_events"

    adjudication_id = Column(String, primary_key=True)
    response_id = Column(String, nullable=False, index=True)
    axis = Column(String, nullable=False, index=True)
    adjudicator_id = Column(String, nullable=False, index=True)
    final_score = Column(Integer, nullable=True)
    resolution_type = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    rubric_version = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


@dataclass(frozen=True)
class RatingInput:
    response_id: str
    rater_id: str
    axis: str
    score: int | None
    rubric_version: str
    comment: str = ""
    context_required: bool = False


@dataclass(frozen=True)
class AdjudicationInput:
    response_id: str
    axis: str
    adjudicator_id: str
    final_score: int | None
    resolution_type: str
    rationale: str
    rubric_version: str


def init_annotation_db(engine: Engine) -> None:
    init_response_db(engine)
    AnnotationBase.metadata.create_all(engine)


def db_engine(db_path: str | Path = "data/annotations.db") -> Engine:
    engine = get_engine(db_path)
    init_annotation_db(engine)
    return engine


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_session(engine: Engine):
    try:
        return sessionmaker(bind=engine, future=True)()
    except TypeError:
        return sessionmaker(bind=engine)()


def append_annotation(engine: Engine, rating: RatingInput) -> str:
    if rating.score is not None and rating.score not in {1, 2, 3, 4}:
        raise ValueError("score must be 1, 2, 3, 4, or None for N/A")
    event_id = str(uuid4())
    session = make_session(engine)
    try:
        session.add(
            AnnotationEvent(
                event_id=event_id,
                response_id=rating.response_id,
                rater_id=rating.rater_id,
                axis=rating.axis,
                score=rating.score,
                rubric_version=rating.rubric_version,
                comment=rating.comment,
                context_required=rating.context_required,
                created_at=utc_now(),
            )
        )
        session.commit()
    finally:
        session.close()
    return event_id


def append_response_rating(
    engine: Engine,
    response_id: str,
    rater_id: str,
    scores: dict[str, int | None],
    rubric_version: str,
    comment: str = "",
    context_required: bool = False,
) -> list[str]:
    return [
        append_annotation(
            engine,
            RatingInput(
                response_id=response_id,
                rater_id=rater_id,
                axis=axis,
                score=score,
                rubric_version=rubric_version,
                comment=comment,
                context_required=context_required,
            ),
        )
        for axis, score in scores.items()
    ]


def append_adjudication(engine: Engine, adjudication: AdjudicationInput) -> str:
    if adjudication.final_score is not None and adjudication.final_score not in {1, 2, 3, 4}:
        raise ValueError("final_score must be 1, 2, 3, 4, or None for N/A")
    if not adjudication.rationale.strip():
        raise ValueError("rationale is required")
    adjudication_id = str(uuid4())
    session = make_session(engine)
    try:
        session.add(
            AdjudicationEvent(
                adjudication_id=adjudication_id,
                response_id=adjudication.response_id,
                axis=adjudication.axis,
                adjudicator_id=adjudication.adjudicator_id,
                final_score=adjudication.final_score,
                resolution_type=adjudication.resolution_type,
                rationale=adjudication.rationale,
                rubric_version=adjudication.rubric_version,
                created_at=utc_now(),
            )
        )
        session.commit()
    finally:
        session.close()
    return adjudication_id


def annotations_df(engine: Engine) -> pd.DataFrame:
    query = "select * from annotation_events order by created_at"
    return pd.read_sql_query(query, engine)


def adjudications_df(engine: Engine) -> pd.DataFrame:
    query = "select * from adjudication_events order by created_at"
    return pd.read_sql_query(query, engine)


def responses_df(engine: Engine) -> pd.DataFrame:
    query = """
    select
        r.response_id,
        r.prompt_id,
        p.category,
        p.source,
        p.prompt_text,
        r.model_provider,
        r.model_name,
        r.response_text,
        r.generation_mode,
        r.created_at
    from model_responses r
    join prompts p on p.prompt_id = r.prompt_id
    order by p.prompt_id, r.model_provider
    """
    return pd.read_sql_query(query, engine)


def next_unrated_response(engine: Engine, rater_id: str, axis_count: int) -> dict | None:
    query = text(
        """
        select r.response_id, p.prompt_text, p.category,
               r.model_provider, r.model_name, r.response_text
        from model_responses r
        join prompts p on p.prompt_id = r.prompt_id
        left join annotation_events a
          on a.response_id = r.response_id and a.rater_id = :rater_id
        group by r.response_id
        having count(a.event_id) < :axis_count
        order by p.prompt_id, r.model_provider
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            query, {"rater_id": rater_id, "axis_count": axis_count}
        ).mappings().first()
        return dict(row) if row else None


def rerate_candidate(engine: Engine, rater_id: str, cooldown_days: int = 7) -> dict | None:
    cutoff = utc_now() - timedelta(days=cooldown_days)
    query = text(
        """
        select r.response_id, p.prompt_text, p.category,
               r.model_provider, r.model_name, r.response_text,
               max(a.created_at) as last_rated_at
        from annotation_events a
        join model_responses r on r.response_id = a.response_id
        join prompts p on p.prompt_id = r.prompt_id
        where a.rater_id = :rater_id
        group by r.response_id
        having datetime(last_rated_at) <= datetime(:cutoff)
        order by last_rated_at asc
        limit 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query, {"rater_id": rater_id, "cutoff": cutoff}).mappings().first()
        return dict(row) if row else None


def create_engine_for_tests() -> Engine:
    try:
        engine = create_engine("sqlite:///:memory:", future=True)
    except TypeError:
        engine = create_engine("sqlite:///:memory:")
    ResponseBase.metadata.create_all(engine)
    AnnotationBase.metadata.create_all(engine)
    return engine
