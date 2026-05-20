from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)

try:
    from sqlalchemy.orm import declarative_base
except ImportError:  # SQLAlchemy < 1.4
    from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base(metadata=MetaData())


class Prompt(Base):
    __tablename__ = "prompts"

    prompt_id = Column(String, primary_key=True)
    category = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    prompt_text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class ModelResponse(Base):
    __tablename__ = "model_responses"

    response_id = Column(String, primary_key=True)
    prompt_id = Column(String, ForeignKey("prompts.prompt_id"), nullable=False, index=True)
    model_provider = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    response_text = Column(Text, nullable=False)
    generation_mode = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("prompt_id", "model_provider", "model_name", name="uq_response_model"),
    )


def get_engine(db_path: str | Path = "data/annotations.db") -> Engine:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return create_engine(f"sqlite:///{path}", future=True)
    except TypeError:
        return create_engine(f"sqlite:///{path}")


def init_response_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_session(engine: Engine):
    try:
        return sessionmaker(bind=engine, future=True)()
    except TypeError:
        return sessionmaker(bind=engine)()


def session_get(session, model, key):
    if hasattr(session, "get"):
        return session.get(model, key)
    return session.query(model).get(key)


def upsert_prompt(
    engine: Engine,
    prompt_id: str,
    category: str,
    source: str,
    prompt_text: str,
    metadata_json: dict | None = None,
) -> None:
    session = make_session(engine)
    try:
        prompt = session_get(session, Prompt, prompt_id)
        if prompt is None:
            session.add(
                Prompt(
                    prompt_id=prompt_id,
                    category=category,
                    source=source,
                    prompt_text=prompt_text,
                    metadata_json=metadata_json or {},
                    created_at=utc_now(),
                )
            )
        else:
            prompt.category = category
            prompt.source = source
            prompt.prompt_text = prompt_text
            prompt.metadata_json = metadata_json or {}
        session.commit()
    finally:
        session.close()


def upsert_response(
    engine: Engine,
    response_id: str,
    prompt_id: str,
    model_provider: str,
    model_name: str,
    response_text: str,
    generation_mode: str,
) -> None:
    session = make_session(engine)
    try:
        response = session_get(session, ModelResponse, response_id)
        if response is None:
            session.add(
                ModelResponse(
                    response_id=response_id,
                    prompt_id=prompt_id,
                    model_provider=model_provider,
                    model_name=model_name,
                    response_text=response_text,
                    generation_mode=generation_mode,
                    created_at=utc_now(),
                )
            )
        else:
            response.response_text = response_text
            response.generation_mode = generation_mode
            response.created_at = utc_now()
        session.commit()
    finally:
        session.close()
