"""
Chunk help tickets for LLM processing to stay within context limits.
"""
from typing import List

import pandas as pd

DEFAULT_CHUNK_SIZE = 150


def get_chunks(
    df: pd.DataFrame,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> List[pd.DataFrame]:
    """
    Split DataFrame into chunks of at most chunk_size rows.

    Keeps Title, Message, and Category together per row. Chunking is sequential
    so that we can process in batches without exceeding token limits.

    Args:
        df: DataFrame with columns Title, Message, Category.
        chunk_size: Maximum number of tickets per chunk.

    Returns:
        List of DataFrames, each of length <= chunk_size.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    chunks = []
    for start in range(0, len(df), chunk_size):
        end = min(start + chunk_size, len(df))
        chunks.append(df.iloc[start:end].copy())
    return chunks
