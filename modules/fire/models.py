"""Small, serializable domain types for Fire / EMS mode."""

from dataclasses import dataclass

GENERAL_MODE = "General"
FIRE_EMS_MODE = "Fire / EMS"


@dataclass(frozen=True)
class CallClassification:
    """Classification metadata while preserving the source incident type."""

    original_type: str
    category: str
    confidence: str
    rule_id: str
