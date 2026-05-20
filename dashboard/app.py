from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation.annotation_store import (
    AdjudicationInput,
    adjudications_df,
    annotations_df,
    append_adjudication,
    db_engine,
    responses_df,
)
from annotation.app import render_rating_form
from annotation.disagreement_detector import detect_disagreements, review_reasons
from annotation.rubric_loader import load_rubric
from eval.adjudication import adjudication_queue
from eval.agreement_metrics import (
    cohen_kappa_by_axis,
    ordinal_krippendorff_alpha,
    pairwise_exact_agreement,
    score_correlation,
)
from eval.coverage_metrics import axis_coverage, category_coverage, response_axis_coverage
from eval.dataset_diagnostics import dataset_quality_diagnostics, diagnostic_summary
from eval.drift_metrics import score_distribution
from eval.edge_case_clustering import cluster_edge_cases
from eval.reports import launch_readiness_report
from eval.scorecards import model_axis_scorecard, model_readiness_scorecard
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
    return engine, rubric, responses_df(engine), annotations_df(engine), adjudications_df(engine)


def page_rate(engine, rubric) -> None:
    st.header("Rate")
    st.caption(
        "This demo uses preloaded prompt and model-response pairs. "
        "The human task is to evaluate each response against the rubric."
    )
    rater_id = st.sidebar.text_input("Rater ID", os.getenv("RATER_ID", "demo_rater"))
    rerate_mode = st.sidebar.toggle("7-day re-rate mode")
    render_rating_form(engine, rubric, rater_id, rerate_mode)


def page_inputs(responses: pd.DataFrame) -> None:
    st.header("Inputs")
    st.caption(
        "These are the prompt and model-response pairs being evaluated. "
        "In a production workflow, this table would come from benchmark prompts, "
        "internal eval sets, or sampled production traffic."
    )
    display_cols = [
        "prompt_id",
        "category",
        "model_provider",
        "model_name",
        "prompt_text",
        "response_text",
    ]
    st.dataframe(
        responses[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "prompt_text": st.column_config.TextColumn("Prompt", width="large"),
            "response_text": st.column_config.TextColumn("Model Response", width="large"),
        },
    )


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


def page_scorecards(responses: pd.DataFrame, events: pd.DataFrame) -> None:
    st.header("Scorecards")
    st.caption(
        "Model-level quality views for launch-readiness conversations. "
        "Scores come from the latest human rating per response and rubric axis."
    )
    readiness = model_readiness_scorecard(responses, events)
    st.subheader("Model Readiness")
    st.dataframe(readiness, use_container_width=True, hide_index=True)
    if not readiness.empty:
        st.plotly_chart(
            px.bar(
                readiness,
                x="model_name",
                y="overall_mean_score",
                color="readiness",
                hover_data=["low_score_rate", "safety_failure_rate"],
            ),
            use_container_width=True,
        )

    axis_card = model_axis_scorecard(responses, events)
    st.subheader("Axis Scorecard")
    st.dataframe(axis_card, use_container_width=True, hide_index=True)
    if not axis_card.empty:
        st.plotly_chart(
            px.bar(
                axis_card,
                x="axis",
                y="mean_score",
                color="model_provider",
                barmode="group",
                facet_col="model_name",
            ),
            use_container_width=True,
        )


def page_diagnostics(rubric, responses: pd.DataFrame, events: pd.DataFrame) -> None:
    st.header("Dataset Diagnostics")
    st.caption(
        "These checks separate prompt/data quality issues from model quality issues: "
        "missing context, high-risk policy boundaries, and incomplete annotation coverage."
    )
    axes = [axis.key for axis in rubric.axes]
    diagnostics = dataset_quality_diagnostics(responses, events, axes)
    summary = diagnostic_summary(diagnostics)
    st.subheader("Diagnostic Summary")
    st.dataframe(summary, use_container_width=True, hide_index=True)
    if not summary.empty:
        st.plotly_chart(
            px.bar(summary, x="issue", y="response_count"),
            use_container_width=True,
        )
    st.subheader("Diagnostic Detail")
    st.dataframe(diagnostics, use_container_width=True, hide_index=True)


def score_choice(label: str) -> int | None:
    return None if label == "N/A" else int(label)


def page_adjudication(
    engine,
    rubric,
    responses: pd.DataFrame,
    events: pd.DataFrame,
    adjudications: pd.DataFrame,
) -> None:
    st.header("Adjudication")
    st.caption(
        "Open review items come from disagreement and context-required signals. "
        "Adjudication records the final quality decision and rationale."
    )
    queue = adjudication_queue(responses, events, adjudications)
    c1, c2 = st.columns(2)
    c1.metric("Open review items", len(queue))
    c2.metric("Adjudicated items", len(adjudications))

    if queue.empty:
        st.success("No open adjudication items.")
    else:
        labels = [
            f"{row.response_id} | {row.axis} | {row.reason} | {row.severity}"
            for row in queue.itertuples()
        ]
        selected_label = st.selectbox("Review item", labels)
        selected = queue.iloc[labels.index(selected_label)]
        st.subheader("Prompt")
        st.info(selected["prompt_text"])
        st.subheader("Model Response")
        st.write(selected["response_text"])
        st.write(
            {
                "axis": selected["axis"],
                "reason": selected["reason"],
                "severity": selected["severity"],
                "latest_scores": selected.get("latest_scores", ""),
                "comments": selected.get("comments", ""),
            }
        )

        with st.form(f"adjudicate::{selected['response_id']}::{selected['axis']}"):
            adjudicator_id = st.text_input(
                "Adjudicator ID", os.getenv("ADJUDICATOR_ID", "lead_reviewer")
            )
            final_score = st.radio("Final score", ["4", "3", "2", "1", "N/A"], horizontal=True)
            resolution_type = st.selectbox(
                "Resolution type",
                ["rubric-ambiguity", "rater-error", "data-issue", "model-quality-issue"],
            )
            rationale = st.text_area("Rationale", placeholder="Why is this the final decision?")
            submitted = st.form_submit_button("Save adjudication")

        if submitted:
            if not rationale.strip():
                st.error("Add a rationale before saving adjudication.")
                return
            append_adjudication(
                engine,
                AdjudicationInput(
                    response_id=selected["response_id"],
                    axis=selected["axis"],
                    adjudicator_id=adjudicator_id,
                    final_score=score_choice(final_score),
                    resolution_type=resolution_type,
                    rationale=rationale,
                    rubric_version=rubric.version,
                ),
            )
            st.success("Adjudication saved.")
            st.rerun()

    st.subheader("Adjudication History")
    st.dataframe(adjudications, use_container_width=True, hide_index=True)


def page_reports(
    rubric,
    responses: pd.DataFrame,
    events: pd.DataFrame,
    adjudications: pd.DataFrame,
) -> None:
    st.header("Exports")
    st.caption("Download production-style artifacts for model review and data quality follow-up.")
    axes = [axis.key for axis in rubric.axes]
    report = launch_readiness_report(responses, events, adjudications, axes)
    st.subheader("Launch Readiness JSON")
    st.json(report)
    st.download_button(
        "Download launch readiness JSON",
        data=json.dumps(report, indent=2),
        file_name="launch_readiness_report.json",
        mime="application/json",
    )
    st.download_button(
        "Download annotations CSV",
        data=events.to_csv(index=False),
        file_name="annotation_events.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download adjudication CSV",
        data=adjudications.to_csv(index=False),
        file_name="adjudication_events.csv",
        mime="text/csv",
    )


def page_edge_cases(
    responses: pd.DataFrame,
    events: pd.DataFrame,
    adjudications: pd.DataFrame,
) -> None:
    st.header("Edge Cases")
    st.subheader("Disagreement Flags")
    st.dataframe(detect_disagreements(events), use_container_width=True)
    st.subheader("Review Reasons")
    st.dataframe(review_reasons(events), use_container_width=True)
    st.subheader("Open Adjudication Queue")
    st.dataframe(adjudication_queue(responses, events, adjudications), use_container_width=True)
    st.subheader("Comment Clusters")
    st.dataframe(cluster_edge_cases(events, responses), use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="LLM Eval Harness", layout="wide")
    st.title("LLM Output Evaluation Harness")
    engine, rubric, responses, events, adjudications = load_data()
    page = st.sidebar.radio(
        "Page",
        [
            "Rate",
            "Inputs",
            "Metrics",
            "Scorecards",
            "Diagnostics",
            "Adjudication",
            "Edge Cases",
            "Exports",
        ],
    )
    if page == "Rate":
        page_rate(engine, rubric)
    elif page == "Inputs":
        page_inputs(responses)
    elif page == "Metrics":
        page_metrics(rubric, responses, events)
    elif page == "Scorecards":
        page_scorecards(responses, events)
    elif page == "Diagnostics":
        page_diagnostics(rubric, responses, events)
    elif page == "Adjudication":
        page_adjudication(engine, rubric, responses, events, adjudications)
    elif page == "Exports":
        page_reports(rubric, responses, events, adjudications)
    else:
        page_edge_cases(responses, events, adjudications)


if __name__ == "__main__":
    main()
