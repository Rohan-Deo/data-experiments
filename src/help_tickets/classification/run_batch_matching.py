"""
CLI to match generated question-bank entries to applicable batches.

Usage (from repo root):
  python -m src.help_tickets.classification.run_batch_matching
  python -m src.help_tickets.classification.run_batch_matching --limit-questions 20 --limit-tickets 500
  python -m src.help_tickets.classification.run_batch_matching --threshold 0.65 --top-k-batches 10

Or from this directory:
  python run_batch_matching.py --limit-questions 20
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# Ensure project root is on path so script works from any cwd
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent.parent
if _project_root not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.help_tickets.classification.batch_matching import (
    build_wide_batch_mapping,
    match_question_bank_to_batches,
)
from src.help_tickets.classification.loader import (
    get_default_batches_path,
    get_default_data_path,
    get_default_question_bank_path,
    load_batches_reference,
    load_help_tickets_with_batch,
    load_question_bank,
)


def get_output_dir() -> Path:
    """Return classification/output directory; create if needed."""
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _deduplicate_long_matches(matches_df: pd.DataFrame) -> pd.DataFrame:
    """Keep the strongest row for each question-batch pair."""
    if matches_df.empty:
        return matches_df

    return (
        matches_df.sort_values(
            by=[
                "question",
                "category",
                "sub_category",
                "batch_id",
                "max_similarity",
                "matched_ticket_count",
            ],
            ascending=[True, True, True, True, False, False],
        )
        .drop_duplicates(
            subset=["question", "category", "sub_category", "batch_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )


def _attach_batch_names(
    matches_df: pd.DataFrame,
    batches_df: pd.DataFrame,
) -> pd.DataFrame:
    """Replace batch_id output with batch_name using the reference CSV."""
    if matches_df.empty:
        return pd.DataFrame(
            columns=[
                "question",
                "category",
                "sub_category",
                "batch_name",
                "max_similarity",
                "matched_ticket_count",
            ]
        )

    enriched = matches_df.merge(batches_df, on="batch_id", how="left")
    enriched["batch_name"] = enriched["batch_name"].fillna(enriched["batch_id"])
    enriched = enriched.drop(columns=["batch_id"])
    return enriched[
        [
            "question",
            "category",
            "sub_category",
            "batch_name",
            "max_similarity",
            "matched_ticket_count",
        ]
    ]


def run(
    question_bank_path: Optional[str] = None,
    tickets_csv_path: Optional[str] = None,
    batches_csv_path: Optional[str] = None,
    output_long_path: Optional[str] = None,
    output_wide_path: Optional[str] = None,
    limit_questions: Optional[int] = None,
    limit_tickets: Optional[int] = None,
    threshold: float = 0.6,
    model_name: str = "all-MiniLM-L6-v2",
    embedding_batch_size: int = 64,
    top_k_batches: Optional[int] = None,
    message_char_limit: int = 1000,
    strategy: str = "embedding",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Match question-bank entries to applicable batches and write outputs.

    Returns:
        (long_matches_df, wide_matches_df)
    """
    question_bank_df = load_question_bank(
        csv_path=question_bank_path,
        limit=limit_questions,
    )
    batches_df = load_batches_reference(csv_path=batches_csv_path)
    tickets_df = load_help_tickets_with_batch(
        csv_path=tickets_csv_path,
        limit=limit_tickets,
    )

    print(
        f"Loaded {len(question_bank_df)} question(s) and {len(tickets_df)} ticket(s) "
        f"for matching (strategy={strategy}, threshold={threshold})."
    )

    long_matches_df = match_question_bank_to_batches(
        question_bank_df=question_bank_df,
        tickets_df=tickets_df,
        threshold=threshold,
        model_name=model_name,
        embedding_batch_size=embedding_batch_size,
        top_k_batches=top_k_batches,
        message_char_limit=message_char_limit,
        strategy=strategy,
    )
    long_matches_df = _deduplicate_long_matches(long_matches_df)
    long_matches_df = _attach_batch_names(long_matches_df, batches_df)
    wide_matches_df = build_wide_batch_mapping(question_bank_df, long_matches_df)

    output_dir = get_output_dir()
    long_path = Path(output_long_path) if output_long_path else output_dir / "question_bank_batch_mapping_long.csv"
    wide_path = Path(output_wide_path) if output_wide_path else output_dir / "question_bank_batch_mapping_wide.csv"
    long_path.parent.mkdir(parents=True, exist_ok=True)
    wide_path.parent.mkdir(parents=True, exist_ok=True)

    long_matches_df.to_csv(long_path, index=False)
    wide_matches_df.to_csv(wide_path, index=False)

    matched_questions = 0 if wide_matches_df.empty else int((wide_matches_df["batch_count"] > 0).sum())
    print(
        f"Saved long-form mapping ({len(long_matches_df)} rows) to {long_path}\n"
        f"Saved wide mapping ({len(wide_matches_df)} rows, {matched_questions} question(s) matched to at least one batch) to {wide_path}"
    )
    return long_matches_df, wide_matches_df


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Match question-bank entries to applicable batches.",
    )
    parser.add_argument(
        "--question-bank",
        type=str,
        default=str(get_default_question_bank_path()),
        help="Path to question_bank.csv.",
    )
    parser.add_argument(
        "--tickets-csv",
        type=str,
        default=str(get_default_data_path()),
        help="Path to help_tickets_raw.csv.",
    )
    parser.add_argument(
        "--batches-csv",
        type=str,
        default=str(get_default_batches_path()),
        help="Path to batches.csv for Batch ID -> Name mapping.",
    )
    parser.add_argument(
        "--output-long",
        type=str,
        default=None,
        help="Long-form output CSV path.",
    )
    parser.add_argument(
        "--output-wide",
        type=str,
        default=None,
        help="Wide output CSV path.",
    )
    parser.add_argument(
        "--limit-questions",
        type=int,
        default=None,
        help="Process only the first N questions (for testing).",
    )
    parser.add_argument(
        "--limit-tickets",
        type=int,
        default=None,
        help="Process only the first N tickets (for testing).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Cosine similarity threshold for a ticket to count as a match (default: 0.6).",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Sentence-transformers model name (default: all-MiniLM-L6-v2).",
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=64,
        help="Embedding batch size for sentence-transformers encoding (default: 64).",
    )
    parser.add_argument(
        "--top-k-batches",
        type=int,
        default=None,
        help="Optional cap on number of batches returned per question.",
    )
    parser.add_argument(
        "--message-char-limit",
        type=int,
        default=1000,
        help="Maximum number of message characters to use per ticket for embeddings (default: 1000).",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="embedding",
        help="Matching strategy: embedding or hybrid (hybrid currently uses category-filtered embeddings).",
    )
    args = parser.parse_args()

    try:
        run(
            question_bank_path=args.question_bank,
            tickets_csv_path=args.tickets_csv,
            batches_csv_path=args.batches_csv,
            output_long_path=args.output_long,
            output_wide_path=args.output_wide,
            limit_questions=args.limit_questions,
            limit_tickets=args.limit_tickets,
            threshold=args.threshold,
            model_name=args.model_name,
            embedding_batch_size=args.embedding_batch_size,
            top_k_batches=args.top_k_batches,
            message_char_limit=args.message_char_limit,
            strategy=args.strategy,
        )
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
