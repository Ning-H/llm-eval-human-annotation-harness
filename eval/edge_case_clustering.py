from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def cluster_edge_cases(
    events: pd.DataFrame,
    responses: pd.DataFrame,
    min_comment_length: int = 8,
    max_clusters: int = 3,
) -> pd.DataFrame:
    if events.empty or responses.empty:
        return pd.DataFrame(
            columns=["cluster", "response_id", "category", "prompt_text", "comment"]
        )

    comments = events[events["comment"].fillna("").str.len() >= min_comment_length].copy()
    if comments.empty:
        return pd.DataFrame(
            columns=["cluster", "response_id", "category", "prompt_text", "comment"]
        )

    joined = comments.merge(responses, on="response_id", how="left")
    text = (
        joined["comment"].fillna("")
        + " "
        + joined["prompt_text"].fillna("")
        + " "
        + joined["category"].fillna("")
    )
    if len(joined) < 2:
        joined["cluster"] = 0
    else:
        vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
        features = vectorizer.fit_transform(text)
        n_clusters = min(max_clusters, len(joined))
        joined["cluster"] = KMeans(
            n_clusters=n_clusters,
            n_init="auto",
            random_state=7,
        ).fit_predict(features)

    return joined[
        [
            "cluster",
            "response_id",
            "category",
            "prompt_text",
            "model_provider",
            "axis",
            "score",
            "comment",
        ]
    ].sort_values(
        ["cluster", "response_id", "axis"]
    )
