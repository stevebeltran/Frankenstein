"""Fire call DataFrame filters."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def filter_fire_calls(frame: pd.DataFrame, categories: Iterable[str] | None = None) -> pd.DataFrame:
    """Filter classified calls without mutating the caller's DataFrame."""
    result = frame.copy()
    if categories is None:
        return result
    selected = {str(value).strip() for value in categories if str(value).strip()}
    if not selected or "fire_category" not in result.columns:
        return result if not selected else result.iloc[0:0].copy()
    return result[result["fire_category"].astype(str).isin(selected)].copy()
