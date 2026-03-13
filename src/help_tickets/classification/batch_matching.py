"""
Match generated question-bank entries to applicable batches.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

SUPPORTED_MATCHING_STRATEGIES = {"embedding", "hybrid"}


def normalize_text(value: str) -> str:
    """Normalize free text for stable comparisons."""
    return " ".join(str(value).strip().lower().split())


def build_ticket_text(row: pd.Series, message_char_limit: int = 1000) -> str:
    """Build a compact semantic text representation for one ticket."""
    title = str(row["Title"]).strip()
    message = str(row["Message"]).strip()
    category = str(row["Category"]).strip()
    if len(message) > message_char_limit:
        message = message[:message_char_limit]
    return f"Category: {category}\nTitle: {title}\nMessage: {message}"


def build_question_text(row: pd.Series) -> str:
    """Build a semantic text representation for one question-bank row."""
    return (
        f"Category: {str(row['category']).strip()}\n"
        f"Sub Category: {str(row['sub_category']).strip()}\n"
        f"Question: {str(row['question']).strip()}"
    )


def prepare_tickets_for_matching(
    tickets_df: pd.DataFrame,
    message_char_limit: int = 1000,
) -> pd.DataFrame:
    """Add normalized category and semantic text fields to ticket rows."""
    df = tickets_df.copy()
    df["category_norm"] = df["Category"].map(normalize_text)
    df["ticket_text"] = df.apply(
        lambda row: build_ticket_text(row, message_char_limit=message_char_limit),
        axis=1,
    )
    return df


def prepare_question_bank_for_matching(question_bank_df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized category and semantic text fields to question-bank rows."""
    df = question_bank_df.copy()
    df["category_norm"] = df["category"].map(normalize_text)
    df["question_text"] = df.apply(build_question_text, axis=1)
    return df


def get_embedding_model(model_name: str) -> SentenceTransformer:
    """Load the sentence-transformers model used for matching."""
    return SentenceTransformer(model_name)


def encode_texts(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int,
) -> np.ndarray:
    """Encode texts into normalized embeddings."""
    return model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def validate_matching_strategy(strategy: str) -> str:
    """Validate and normalize the requested matching strategy."""
    normalized = normalize_text(strategy).replace(" ", "-")
    if normalized not in SUPPORTED_MATCHING_STRATEGIES:
        raise ValueError(
            f"Unsupported strategy '{strategy}'. Supported: {sorted(SUPPORTED_MATCHING_STRATEGIES)}"
        )
    return normalized


def _build_ticket_embedding_index(
    tickets_df: pd.DataFrame,
    model: SentenceTransformer,
    embedding_batch_size: int,
) -> Dict[str, tuple[pd.DataFrame, np.ndarray]]:
    """Precompute ticket embeddings grouped by normalized category."""
    index: Dict[str, tuple[pd.DataFrame, np.ndarray]] = {}
    for category_norm, category_df in tickets_df.groupby("category_norm", sort=False):
        category_df = category_df.reset_index(drop=True)
        embeddings = encode_texts(
            model=model,
            texts=category_df["ticket_text"].tolist(),
            batch_size=embedding_batch_size,
        )
        index[category_norm] = (category_df, embeddings)
    return index


def _match_one_question_to_batches(
    question_row: pd.Series,
    question_embedding: np.ndarray,
    category_ticket_df: pd.DataFrame,
    category_ticket_embeddings: np.ndarray,
    threshold: float,
    top_k_batches: Optional[int],
) -> pd.DataFrame:
    """Return matching batches for one question within one category slice."""
    scores = category_ticket_embeddings @ question_embedding
    match_mask = scores >= threshold
    if not np.any(match_mask):
        return pd.DataFrame(
            columns=[
                "question",
                "category",
                "sub_category",
                "batch_id",
                "max_similarity",
                "matched_ticket_count",
            ]
        )

    matched = category_ticket_df.loc[match_mask, ["Batch ID"]].copy()
    matched["similarity"] = scores[match_mask]
    matched = matched.rename(columns={"Batch ID": "batch_id"})

    grouped = (
        matched.groupby("batch_id", as_index=False)
        .agg(
            max_similarity=("similarity", "max"),
            matched_ticket_count=("similarity", "size"),
        )
        .sort_values(
            by=["max_similarity", "matched_ticket_count", "batch_id"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )

    if top_k_batches is not None:
        grouped = grouped.head(top_k_batches).reset_index(drop=True)

    grouped.insert(0, "sub_category", str(question_row["sub_category"]).strip())
    grouped.insert(0, "category", str(question_row["category"]).strip())
    grouped.insert(0, "question", str(question_row["question"]).strip())
    grouped["max_similarity"] = grouped["max_similarity"].round(6)
    return grouped


def match_question_bank_to_batches(
    question_bank_df: pd.DataFrame,
    tickets_df: pd.DataFrame,
    threshold: float = 0.6,
    model_name: str = "all-MiniLM-L6-v2",
    embedding_batch_size: int = 64,
    top_k_batches: Optional[int] = None,
    message_char_limit: int = 1000,
    strategy: str = "embedding",
) -> pd.DataFrame:
    """
    Match each question-bank row to applicable batches using semantic similarity.

    Strategy notes:
    - ``embedding``: category-filtered semantic matching.
    - ``hybrid``: currently the same implementation, since category pre-filtering
      is already used as the lightweight heuristic layer.
    """
    strategy = validate_matching_strategy(strategy)
    _ = strategy  # reserved for future branching

    prepared_questions = prepare_question_bank_for_matching(question_bank_df)
    prepared_tickets = prepare_tickets_for_matching(
        tickets_df,
        message_char_limit=message_char_limit,
    )

    model = get_embedding_model(model_name)
    question_embeddings = encode_texts(
        model=model,
        texts=prepared_questions["question_text"].tolist(),
        batch_size=embedding_batch_size,
    )
    ticket_index = _build_ticket_embedding_index(
        tickets_df=prepared_tickets,
        model=model,
        embedding_batch_size=embedding_batch_size,
    )

    matches = []
    for idx, question_row in prepared_questions.iterrows():
        category_norm = question_row["category_norm"]
        if category_norm not in ticket_index:
            continue

        category_ticket_df, category_ticket_embeddings = ticket_index[category_norm]
        question_matches = _match_one_question_to_batches(
            question_row=question_row,
            question_embedding=question_embeddings[idx],
            category_ticket_df=category_ticket_df,
            category_ticket_embeddings=category_ticket_embeddings,
            threshold=threshold,
            top_k_batches=top_k_batches,
        )
        if not question_matches.empty:
            matches.append(question_matches)

    if not matches:
        return pd.DataFrame(
            columns=[
                "question",
                "category",
                "sub_category",
                "batch_id",
                "max_similarity",
                "matched_ticket_count",
            ]
        )

    return pd.concat(matches, ignore_index=True)


def build_wide_batch_mapping(
    question_bank_df: pd.DataFrame,
    long_matches_df: pd.DataFrame,
) -> pd.DataFrame:
    """Convert long-form batch matches into one row per question."""
    wide_df = question_bank_df.copy()
    if long_matches_df.empty:
        wide_df["batch_count"] = 0
        wide_df["batch_names"] = ""
        return wide_df

    grouped = (
        long_matches_df.sort_values(
            by=["question", "category", "sub_category", "max_similarity", "matched_ticket_count", "batch_name"],
            ascending=[True, True, True, False, False, True],
        )
        .groupby(["question", "category", "sub_category"], as_index=False)
        .agg(
            batch_count=("batch_name", "nunique"),
            batch_names=("batch_name", lambda values: ",".join(dict.fromkeys(values))),
        )
    )

    wide_df = wide_df.merge(
        grouped,
        on=["question", "category", "sub_category"],
        how="left",
    )
    wide_df["batch_count"] = wide_df["batch_count"].fillna(0).astype(int)
    wide_df["batch_names"] = wide_df["batch_names"].fillna("")
    return wide_df
