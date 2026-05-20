from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation.annotation_store import annotations_df, db_engine, responses_df
from annotation.app import render_rating_form
from annotation.disagreement_detector import detect_disagreements, review_reasons
from annotation.rubric_loader import load_rubric
from eval.agreement_metrics import (
    cohen_kappa_by_axis,
    ordinal_krippendorff_alpha,
    pairwise_exact_agreement,
    score_correlation,
)
from eval.coverage_metrics import axis_coverage, category_coverage, response_axis_coverage
from eval.drift_metrics import score_distribution
from eval.edge_case_clustering import cluster_edge_cases
from scripts.seed_demo_annotations import main as seed_demo_annotations


def ensure_demo_data(db_path: str) -> None:
    if Path(db_path).exists():
        return
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    previous_db_path = os.environ.get("ANNOTATION_DB_PATH")
    os.environ["ANNOTATION_DB_PATH"] = db_path
    try:
        seed_demo_annotations()
    finally:
        if previous_db_path is None:
            os.environ.pop("ANNOTATION_DB_PATH", None)
        else:
            os.environ["ANNOTATION_DB_PATH"] = previous_db_path


def load_data():
    db_path = os.getenv("ANNOTATION_DB_PATH", "data/annotations.db")
    ensure_demo_data(db_path)
    engine = db_engine(db_path)
    rubric = load_rubric("docs/RUBRIC.md")
    return engine, rubric, responses_df(engine), annotations_df(engine)


def page_rate(engine, rubric) -> None:
    st.header("Rate")
    rater_id = st.sidebar.text_input("Rater ID", os.getenv("RATER_ID", "demo_rater"))
    rerate_mode = st.sidebar.toggle("7-day re-rate mode")
    render_rating_form(engine, rubric, rater_id, rerate_mode)


def page_metrics(rubric, responses: pd.DataFrame, events: pd.DataFrame) -> None:
    st.header("Metrics")
    axes = [axis.key for axis in rubric.axes]

    c1, c2, c3 = st.columns(3)
    c1.metric("Responses", len(responses))
    c2.metric("Annotation events", len(events))
    c3.metric("Krippendorff alpha", f"{ordinal_krippendorff_alpha(events):.2f}")

    st.subheader("Coverage")
    coverage = response_axis_coverage(responses, events, axes)
    st.dataframe(category_coverage(responses, events, axes), use_container_width=True)
    if not coverage.empty:
        st.plotly_chart(
            px.histogram(coverage, x="coverage", color="model_provider", nbins=10),
            use_container_width=True,
        )
    st.dataframe(axis_coverage(events, axes), use_container_width=True)

    st.subheader("Agreement")
    st.dataframe(pairwise_exact_agreement(events), use_container_width=True)
    st.dataframe(cohen_kappa_by_axis(events), use_container_width=True)
    st.dataframe(score_correlation(events), use_container_width=True)

    st.subheader("Score Distributions")
    dist = score_distribution(events)
    if not dist.empty:
        st.plotly_chart(
            px.bar(
                dist,
                x="score",
                y="count",
                color="axis",
                facet_col="rubric_version",
                barmode="group",
            ),
            use_container_width=True,
        )


def page_edge_cases(responses: pd.DataFrame, events: pd.DataFrame) -> None:
    st.header("Edge Cases")
    st.subheader("Disagreement Flags")
    st.dataframe(detect_disagreements(events), use_container_width=True)
    st.subheader("Review Reasons")
    st.dataframe(review_reasons(events), use_container_width=True)
    st.subheader("Comment Clusters")
    st.dataframe(cluster_edge_cases(events, responses), use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="LLM Eval Harness", layout="wide")
    st.title("LLM Output Evaluation Harness")
    engine, rubric, responses, events = load_data()
    page = st.sidebar.radio("Page", ["Rate", "Metrics", "Edge Cases"])
    if page == "Rate":
        page_rate(engine, rubric)
    elif page == "Metrics":
        page_metrics(rubric, responses, events)
    else:
        page_edge_cases(responses, events)


if __name__ == "__main__":
    main()
