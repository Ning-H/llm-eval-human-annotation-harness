from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation.annotation_store import (
    append_response_rating,
    db_engine,
    next_unrated_response,
    rerate_candidate,
)
from annotation.rubric_loader import Rubric, load_rubric


def score_choice(label: str) -> int | None:
    return None if label == "N/A" else int(label)


def render_rating_form(engine, rubric: Rubric, rater_id: str, rerate_mode: bool = False) -> None:
    response = (
        rerate_candidate(engine, rater_id, cooldown_days=7)
        if rerate_mode
        else next_unrated_response(engine, rater_id, axis_count=len(rubric.axes))
    )

    if response is None:
        st.info("No eligible responses found for this mode.")
        return

    st.caption(f"Rubric {rubric.version} | response_id: {response['response_id']}")
    st.subheader("Evaluation Input")
    meta_cols = st.columns(3)
    meta_cols[0].metric("Prompt Category", response["category"])
    meta_cols[1].metric("Model Provider", response["model_provider"])
    meta_cols[2].metric("Model", response["model_name"])

    prompt_col, response_col = st.columns(2)
    with prompt_col:
        st.markdown("#### Prompt")
        st.info(response["prompt_text"])
    with response_col:
        st.markdown("#### Model Response")
        st.write(response["response_text"])

    st.divider()
    st.subheader("Human Rubric Rating")

    with st.form(f"rating::{response['response_id']}"):
        scores: dict[str, int | None] = {}
        for axis in rubric.axes:
            st.markdown(f"#### {axis.name}")
            options = ["4", "3", "2", "1", "N/A"]
            labels = {
                key: f"{key}: {value}"
                for key, value in axis.scores.items()
            }
            selected = st.radio(
                axis.key,
                options,
                format_func=lambda option, labels=labels: labels.get(option, option),
                horizontal=False,
            )
            scores[axis.key] = score_choice(selected)
            if axis.guidance:
                with st.expander(f"{axis.name} guidance"):
                    for item in axis.guidance:
                        st.write(f"- {item}")

        context_required = st.checkbox("Context required")
        comment = st.text_area(
            "Comment",
            placeholder="Required for low scores, N/A, ambiguity, or policy uncertainty.",
        )
        submitted = st.form_submit_button("Save annotation")

    if submitted:
        low_or_na = any(score in {1, 2, None} for score in scores.values())
        if low_or_na and not comment.strip():
            st.error("Add a comment for scores of 1, 2, or N/A.")
            return
        append_response_rating(
            engine,
            response_id=response["response_id"],
            rater_id=rater_id,
            scores=scores,
            rubric_version=rubric.version,
            comment=comment,
            context_required=context_required,
        )
        st.success("Annotation saved.")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="LLM Eval Rating", layout="wide")
    st.title("LLM Output Rating")
    db_path = os.getenv("ANNOTATION_DB_PATH", "data/annotations.db")
    engine = db_engine(db_path)
    rubric = load_rubric("docs/RUBRIC.md")
    rater_id = st.sidebar.text_input("Rater ID", os.getenv("RATER_ID", "demo_rater"))
    rerate_mode = st.sidebar.toggle("7-day re-rate mode")
    render_rating_form(engine, rubric, rater_id, rerate_mode=rerate_mode)


if __name__ == "__main__":
    main()
