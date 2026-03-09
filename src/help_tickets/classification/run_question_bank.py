"""
CLI to generate a question bank from help tickets using OpenAI (gpt-5.1).

Usage (from repo root):
  python -m src.help_tickets.classification.run_question_bank
  python -m src.help_tickets.classification.run_question_bank --limit 500
  python -m src.help_tickets.classification.run_question_bank --limit 100 --chunk-size 50
  python -m src.help_tickets.classification.run_question_bank --workers 10
  python -m src.help_tickets.classification.run_question_bank --chunk-question-cap 8 --final-question-cap 325

Or from this directory:
  python run_question_bank.py --limit 500
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Ensure project root is on path so script works from any cwd
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent.parent
if _project_root not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.help_tickets.classification.chunking import get_chunks
from src.help_tickets.classification.loader import load_help_tickets
from src.help_tickets.classification.llm_client import get_question_bank_from_prompt
from src.help_tickets.classification.prompts import (
    build_consolidation_prompt,
    build_question_bank_prompt,
)


def get_output_dir() -> Path:
    """Return classification/output directory; create if needed."""
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _normalize_text(value: str) -> str:
    """Normalize text for exact deduplication."""
    return " ".join(str(value).strip().lower().split())


def _aggregate_candidates(rows: List[dict]) -> pd.DataFrame:
    """Aggregate exact duplicate candidates and attach support counts."""
    if not rows:
        return pd.DataFrame(columns=["question", "category", "sub_category", "support_count"])

    df = pd.DataFrame(rows)
    df["_q_norm"] = df["question"].map(_normalize_text)
    df["_c_norm"] = df["category"].map(_normalize_text)
    df["_s_norm"] = df["sub_category"].map(_normalize_text)

    grouped = (
        df.groupby(["_q_norm", "_c_norm", "_s_norm"], as_index=False)
        .agg(
            question=("question", "first"),
            category=("category", "first"),
            sub_category=("sub_category", "first"),
            support_count=("question", "size"),
        )
        .sort_values(
            by=["support_count", "category", "sub_category", "question"],
            ascending=[False, True, True, True],
        )
        .reset_index(drop=True)
    )
    return grouped[["question", "category", "sub_category", "support_count"]]


def _process_chunk(
    args: Tuple[int, pd.DataFrame, int, int]
) -> Tuple[int, List[dict]]:
    """Process a single chunk: build prompt, call LLM, return (chunk_index, results)."""
    chunk_index, chunk, total_chunks, chunk_question_cap = args
    prompt = build_question_bank_prompt(
        chunk,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        max_questions=chunk_question_cap,
    )
    results = get_question_bank_from_prompt(prompt)
    return (chunk_index, results)


def run(
    limit: Optional[int] = None,
    chunk_size: int = 150,
    csv_path: Optional[str] = None,
    output_path: Optional[str] = None,
    workers: int = 8,
    chunk_question_cap: int = 8,
    final_question_cap: int = 325,
    final_question_floor: int = 300,
) -> pd.DataFrame:
    """
    Load tickets, chunk, call LLM per chunk (in parallel), aggregate and return question bank.

    Args:
        limit: If set, use only first N records.
        chunk_size: Tickets per API call.
        csv_path: Override path to help_tickets_raw.csv.
        output_path: Override path for output CSV.
        workers: Max parallel OpenAI API calls (default: 8).
        chunk_question_cap: Max questions each chunk may emit.
        final_question_cap: Hard cap for final output.
        final_question_floor: Preferred lower bound for consolidation target.

    Returns:
        DataFrame with columns question, category, sub_category.
    """
    df = load_help_tickets(csv_path=csv_path, limit=limit)
    if df.empty:
        print("No tickets to process.")
        return pd.DataFrame(columns=["question", "category", "sub_category"])
    if chunk_question_cap <= 0:
        raise ValueError("chunk_question_cap must be positive")
    if final_question_cap <= 0:
        raise ValueError("final_question_cap must be positive")
    if final_question_floor <= 0:
        raise ValueError("final_question_floor must be positive")
    if final_question_floor > final_question_cap:
        raise ValueError("final_question_floor cannot be greater than final_question_cap")

    chunks = get_chunks(df, chunk_size=chunk_size)
    total_chunks = len(chunks)
    print(
        "Processing "
        f"{len(df)} tickets in {total_chunks} chunk(s) "
        f"(chunk_size={chunk_size}, workers={workers}, chunk_question_cap={chunk_question_cap}, "
        f"final_question_cap={final_question_cap})."
    )

    chunk_args = [
        (i, chunk, total_chunks, chunk_question_cap)
        for i, chunk in enumerate(chunks)
    ]
    chunk_results: Dict[int, List[dict]] = {}
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_process_chunk, arg): arg[0] for arg in chunk_args}
        for future in as_completed(futures):
            chunk_index = futures[future]
            try:
                idx, results = future.result()
                chunk_results[idx] = results
                completed += 1
                pct = 100 * completed // total_chunks
                print(f"  Chunk {idx + 1}/{total_chunks} done ({len(results)} questions) — progress: {completed}/{total_chunks} chunks ({pct}%)")
            except Exception as e:
                print(f"  Chunk {chunk_index + 1}/{total_chunks} ERROR: {e}")
                raise
    print(f"All {total_chunks} chunks completed.")

    all_rows = []
    for i in range(total_chunks):
        all_rows.extend(chunk_results[i])

    candidate_df = _aggregate_candidates(all_rows)
    if candidate_df.empty:
        result_df = pd.DataFrame(columns=["question", "category", "sub_category"])
    else:
        print(
            "Chunk stage produced "
            f"{len(all_rows)} candidate questions, "
            f"{len(candidate_df)} unique exact candidates after aggregation."
        )
        print(
            "Starting final consolidation "
            f"(target range: {final_question_floor}-{final_question_cap}, "
            f"input candidates: {len(candidate_df)})."
        )
        consolidation_prompt = build_consolidation_prompt(
            candidate_rows=candidate_df.to_dict("records"),
            min_questions=final_question_floor,
            max_questions=final_question_cap,
        )
        consolidated_rows = get_question_bank_from_prompt(consolidation_prompt)
        result_df = _aggregate_candidates(consolidated_rows)[
            ["question", "category", "sub_category"]
        ]
        if len(result_df) > final_question_cap:
            result_df = result_df.head(final_question_cap).reset_index(drop=True)
        print(f"Final consolidation produced {len(result_df)} questions.")

    out_path = output_path or str(get_output_dir() / "question_bank.csv")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(out_path, index=False)
    print(f"Saved {len(result_df)} questions to {out_path}")
    return result_df


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate question bank from help tickets using OpenAI gpt-5.1.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N records (for testing). Default: all.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=150,
        help="Number of tickets per API call (default: 150).",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to help_tickets_raw.csv (default: classification/data/help_tickets_raw.csv).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: classification/output/question_bank.csv).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Max parallel OpenAI API calls (default: 8).",
    )
    parser.add_argument(
        "--chunk-question-cap",
        type=int,
        default=8,
        help="Max candidate questions each chunk may emit (default: 8).",
    )
    parser.add_argument(
        "--final-question-cap",
        type=int,
        default=325,
        help="Hard cap for final output question count (default: 325).",
    )
    parser.add_argument(
        "--final-question-floor",
        type=int,
        default=300,
        help="Preferred lower target for final consolidation (default: 300).",
    )
    args = parser.parse_args()

    try:
        run(
            limit=args.limit,
            chunk_size=args.chunk_size,
            csv_path=args.csv,
            output_path=args.output,
            workers=args.workers,
            chunk_question_cap=args.chunk_question_cap,
            final_question_cap=args.final_question_cap,
            final_question_floor=args.final_question_floor,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
