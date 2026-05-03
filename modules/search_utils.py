"""
Shared utilities for address and facility search operations.

Contains common text normalization, scoring, and candidate filtering logic used
across address searches and public facility searches.
"""

from typing import Any, Dict, List, Optional


def normalize_search_text(value: str) -> str:
    """Normalize text for search and comparison.

    Removes extra whitespace, converts to lowercase, handles special characters.

    Args:
        value: Text to normalize

    Returns:
        Normalized text string
    """
    if not value:
        return ""
    text = str(value).strip().lower()
    # Remove extra whitespace
    text = " ".join(text.split())
    return text


def is_probably_coordinate(text: str) -> bool:
    """Check if text looks like latitude/longitude coordinates.

    Args:
        text: Text to check

    Returns:
        True if text appears to be coordinates
    """
    text = text.strip()
    # Simple check: if it has digits, decimal points, and possibly negative signs/commas
    parts = text.replace(",", " ").split()
    if len(parts) < 2:
        return False
    try:
        float(parts[0])
        float(parts[1])
        return True
    except ValueError:
        return False


def score_location_match(
    candidate: Dict[str, Any],
    preferred_city: str = "",
    preferred_state: str = "",
) -> float:
    """Score a location candidate based on match quality and preference match.

    Higher scores indicate better matches.

    Args:
        candidate: Candidate dict with 'address', 'city', 'state' fields
        preferred_city: Preferred city (bonus points if matched)
        preferred_state: Preferred state (bonus points if matched)

    Returns:
        Score between 0.0 and 1.0
    """
    score = 0.5  # Base score for any valid candidate

    # Match preferred state
    if preferred_state and candidate.get("state", "").upper() == preferred_state.upper():
        score += 0.3

    # Match preferred city
    if preferred_city:
        cand_city = candidate.get("city", "").lower()
        pref_city = preferred_city.lower()
        if cand_city == pref_city:
            score += 0.2
        elif cand_city.startswith(pref_city) or pref_city.startswith(cand_city):
            score += 0.1

    return min(score, 1.0)


def deduplicate_candidates(
    candidates: List[Dict[str, Any]], key: str = "address"
) -> List[Dict[str, Any]]:
    """Remove duplicate candidates based on a key field.

    Args:
        candidates: List of candidate dicts
        key: Field to use for deduplication (default: 'address')

    Returns:
        Deduplicated list preserving order
    """
    seen = set()
    deduped = []
    for candidate in candidates:
        val = str(candidate.get(key, "")).lower().strip()
        if val and val not in seen:
            seen.add(val)
            deduped.append(candidate)
    return deduped
