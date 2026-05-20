from __future__ import annotations

import pandas as pd


def dataset_quality_diagnostics(
    responses: pd.DataFrame,
    events: pd.DataFrame,
    expected_axes: list[str],
) -> pd.DataFrame:
    rows: list[dict] = []
    rated_axes = (
        events.drop_duplicates(["response_id", "axis"])
        .groupby("response_id")["axis"]
        .nunique()
        if not events.empty
        else pd.Series(dtype=int)
    )
    context_required = (
        set(events.loc[events["context_required"] == True, "response_id"])  # noqa: E712
        if not events.empty
        else set()
    )

    for response in responses.itertuples():
        issues = []
        prompt = str(response.prompt_text)
        category = str(response.category)
        coverage = rated_axes.get(response.response_id, 0) / max(len(expected_axes), 1)
        if coverage < 1:
            issues.append("incomplete-axis-coverage")
        if response.response_id in context_required or category == "missing_context":
            issues.append("context-required")
        if len(prompt.split()) < 5:
            issues.append("short-or-underspecified-prompt")
        if any(term in prompt.lower() for term in ["previous", "answer a or b", "based on"]):
            issues.append("missing-reference-risk")
        if category in {"safety", "refusal"}:
            issues.append("high-risk-policy-boundary")
        if not issues:
            issues.append("no-diagnostic-issue")
        for issue in issues:
            rows.append(
                {
                    "response_id": response.response_id,
                    "prompt_id": response.prompt_id,
                    "category": category,
                    "model_provider": response.model_provider,
                    "issue": issue,
                    "coverage": coverage,
                }
            )
    return pd.DataFrame(rows)


def diagnostic_summary(diagnostics: pd.DataFrame) -> pd.DataFrame:
    if diagnostics.empty:
        return pd.DataFrame(columns=["issue", "response_count"])
    return (
        diagnostics.groupby("issue")["response_id"]
        .nunique()
        .rename("response_count")
        .reset_index()
        .sort_values("response_count", ascending=False)
    )
