"""
Load CSV inputs used by the classification workflows.
"""
import os
from pathlib import Path
from typing import Optional

import pandas as pd

QUESTION_BANK_COLUMNS = ["question", "category", "sub_category"]
QUESTION_BANK_REQUIRED_COLUMNS = ["question", "category"]
TICKET_COLUMNS = ["Title", "Message", "Category"]
TICKET_WITH_BATCH_COLUMNS = ["Batch ID", "Title", "Message", "Category"]
BATCH_REFERENCE_COLUMNS = ["ID", "Name"]


def get_default_data_path() -> Path:
    """Return default path to help_tickets_raw.csv in classification/data."""
    return Path(__file__).resolve().parent / "data" / "help_tickets_raw.csv"


def get_default_question_bank_path() -> Path:
    """Return default path to generated question_bank.csv in classification/output."""
    return Path(__file__).resolve().parent / "output" / "question_bank.csv"


def get_default_batches_path() -> Path:
    """Return default path to batches.csv in classification/data."""
    return Path(__file__).resolve().parent / "data" / "batches.csv"


def _load_csv(path: Path) -> pd.DataFrame:
    """Read a CSV from disk as strings."""
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path, dtype=str)


def _validate_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    """Ensure all required columns exist in the DataFrame."""
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV must contain column: {col}")


def _clean_ticket_rows(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    """Drop rows missing required ticket fields and trim whitespace-only text."""
    df = df[required_columns].copy()
    df = df.dropna(subset=required_columns)
    for col in required_columns:
        df[col] = df[col].astype(str)

    for text_col in ["Title", "Message", "Category"]:
        if text_col in df.columns:
            df = df[df[text_col].str.strip() != ""]

    if "Batch ID" in df.columns:
        df = df[df["Batch ID"].str.strip() != ""]

    return df.reset_index(drop=True)


def load_help_tickets(
    csv_path: Optional[os.PathLike | str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load help tickets from CSV with Title, Message, and Category.

    Args:
        csv_path: Path to CSV. If None, uses classification/data/help_tickets_raw.csv.
        limit: If set, return only the first `limit` records (for testing).

    Returns:
        DataFrame with columns Title, Message, Category. Drops rows where any
        of these are missing.
    """
    path = Path(csv_path) if csv_path else get_default_data_path()
    df = _load_csv(path)
    _validate_columns(df, TICKET_COLUMNS)
    df = _clean_ticket_rows(df, TICKET_COLUMNS)

    if limit is not None:
        df = df.head(int(limit))

    return df.reset_index(drop=True)


def load_help_tickets_with_batch(
    csv_path: Optional[os.PathLike | str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load help tickets with Batch ID for question-to-batch matching.

    Args:
        csv_path: Path to CSV. If None, uses classification/data/help_tickets_raw.csv.
        limit: If set, return only the first `limit` records.

    Returns:
        DataFrame with columns Batch ID, Title, Message, Category.
    """
    path = Path(csv_path) if csv_path else get_default_data_path()
    df = _load_csv(path)
    _validate_columns(df, TICKET_WITH_BATCH_COLUMNS)
    df = _clean_ticket_rows(df, TICKET_WITH_BATCH_COLUMNS)

    if limit is not None:
        df = df.head(int(limit))

    return df.reset_index(drop=True)


def load_question_bank(
    csv_path: Optional[os.PathLike | str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load a generated question bank CSV.

    Args:
        csv_path: Path to question_bank.csv. If None, uses classification/output/question_bank.csv.
        limit: If set, return only the first `limit` rows.

    Returns:
        DataFrame with columns question, category, sub_category.
    """
    path = Path(csv_path) if csv_path else get_default_question_bank_path()
    df = _load_csv(path)
    _validate_columns(df, QUESTION_BANK_REQUIRED_COLUMNS)

    if "sub_category" not in df.columns:
        df["sub_category"] = df["category"]

    df = df[QUESTION_BANK_COLUMNS].copy()
    df = df.dropna(subset=["question", "category"])
    df["question"] = df["question"].astype(str)
    df["category"] = df["category"].astype(str)
    df["sub_category"] = df["sub_category"].astype(str)
    df = df[df["question"].str.strip() != ""]
    df = df[df["category"].str.strip() != ""]
    df["sub_category"] = df["sub_category"].replace("", pd.NA).fillna(df["category"])

    if limit is not None:
        df = df.head(int(limit))

    return df.reset_index(drop=True)


def load_batches_reference(
    csv_path: Optional[os.PathLike | str] = None,
) -> pd.DataFrame:
    """
    Load the Batch ID -> Name reference mapping from batches.csv.

    Args:
        csv_path: Path to batches.csv. If None, uses classification/data/batches.csv.

    Returns:
        DataFrame with columns batch_id and batch_name.
    """
    path = Path(csv_path) if csv_path else get_default_batches_path()
    df = _load_csv(path)
    _validate_columns(df, BATCH_REFERENCE_COLUMNS)
    df = df[BATCH_REFERENCE_COLUMNS].copy()
    df = df.dropna(subset=BATCH_REFERENCE_COLUMNS)
    df["ID"] = df["ID"].astype(str)
    df["Name"] = df["Name"].astype(str)
    df = df[df["ID"].str.strip() != ""]
    df = df[df["Name"].str.strip() != ""]
    df = df.rename(columns={"ID": "batch_id", "Name": "batch_name"})
    return df.drop_duplicates(subset=["batch_id"], keep="first").reset_index(drop=True)
