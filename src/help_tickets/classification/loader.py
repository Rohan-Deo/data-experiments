"""
Load help tickets from CSV for question-bank generation.
"""
import os
from pathlib import Path
from typing import Optional

import pandas as pd

REQUIRED_COLUMNS = ["Title", "Message", "Category"]


def get_default_data_path() -> Path:
    """Return default path to help_tickets_raw.csv in classification/data."""
    return Path(__file__).resolve().parent / "data" / "help_tickets_raw.csv"


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
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path, dtype=str)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"CSV must contain column: {col}")

    df = df[REQUIRED_COLUMNS].copy()
    df = df.dropna(subset=REQUIRED_COLUMNS)
    df = df[df["Title"].str.strip() != ""]
    df = df[df["Message"].str.strip() != ""]

    if limit is not None:
        df = df.head(int(limit))

    return df.reset_index(drop=True)
