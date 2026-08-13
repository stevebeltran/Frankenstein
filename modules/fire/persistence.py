"""Backward-compatible Fire mode session payload helpers."""

from __future__ import annotations

from collections.abc import Mapping

from .models import GENERAL_MODE

FIRE_SESSION_VERSION = 1


def fire_session_defaults() -> dict:
    return {
        "version": FIRE_SESSION_VERSION,
        "mode": GENERAL_MODE,
        "fire_enabled": False,
        "category_filter": [],
        "dataset_recommendation": False,
    }


def merge_fire_session(payload: Mapping | None) -> dict:
    result = fire_session_defaults()
    if isinstance(payload, Mapping):
        result.update({key: payload[key] for key in result if key in payload})
    result["version"] = FIRE_SESSION_VERSION
    result["category_filter"] = list(result.get("category_filter") or [])
    result["fire_enabled"] = bool(result["fire_enabled"])
    result["dataset_recommendation"] = bool(result["dataset_recommendation"])
    return result
