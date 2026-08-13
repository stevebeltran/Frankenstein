"""Deterministic Fire / EMS call classification."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from .models import CallClassification


_RULES = (
    ("structure_fire", ("structure fire", "building fire", "house fire", "commercial fire")),
    ("wildland_fire", ("wildland", "brush fire", "grass fire", "forest fire")),
    ("hazmat", ("hazmat", "hazardous material", "chemical spill", "gas leak")),
    ("rescue", ("technical rescue", "water rescue", "search and rescue", "rescue")),
    ("mva", ("traffic collision", "motor vehicle", "vehicle crash", "car accident", "mva")),
    ("medical", ("ems", "medical", "chest pain", "difficulty breathing", "cardiac", "overdose")),
)


def classify_call(incident_type: object, agency: object = "") -> CallClassification:
    original = "" if incident_type is None else str(incident_type)
    text = re.sub(r"\s+", " ", original.strip().lower())
    agency_text = "" if agency is None else str(agency).strip().lower()
    for category, phrases in _RULES:
        if any(phrase in text for phrase in phrases):
            return CallClassification(original, category, "high", category)
    if agency_text in {"fire", "fire/ems", "ems", "medical"}:
        category = "medical" if agency_text in {"ems", "medical"} else "other"
        return CallClassification(original, category, "medium", f"agency_{agency_text.replace('/', '_')}")
    return CallClassification(original, "other", "low", "unclassified")


def _incident_column(frame: pd.DataFrame) -> str | None:
    for name in ("incident_type", "call_type_desc", "call_type", "type"):
        if name in frame.columns:
            return name
    return None


def classify_calls(frame: pd.DataFrame, incident_column: str | None = None) -> pd.DataFrame:
    """Return a copy with Fire metadata; source columns are never overwritten."""
    result = frame.copy()
    column = incident_column or _incident_column(result)
    if column is None:
        values = [classify_call("", agency) for agency in result.get("agency", pd.Series("", index=result.index))]
    else:
        values = [classify_call(value, agency) for value, agency in zip(result[column], result.get("agency", pd.Series("", index=result.index)))]
    result["fire_category"] = [item.category for item in values]
    result["fire_classification_confidence"] = [item.confidence for item in values]
    result["fire_classification_rule"] = [item.rule_id for item in values]
    return result


def recommend_fire_mode(frame: pd.DataFrame, threshold: float = 0.2) -> bool:
    """Return a non-binding recommendation when enough calls look Fire/EMS-related."""
    if frame is None or frame.empty:
        return False
    classified = classify_calls(frame)
    fire_categories = {"structure_fire", "wildland_fire", "hazmat", "rescue", "medical"}
    share = float(classified["fire_category"].isin(fire_categories).mean())
    return share >= float(threshold)
