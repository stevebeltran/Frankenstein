import pandas as pd

from modules.fire.classification import classify_call, classify_calls, recommend_fire_mode
from modules.fire.models import FIRE_EMS_MODE, GENERAL_MODE
from modules.fire.persistence import FIRE_SESSION_VERSION, fire_session_defaults, merge_fire_session
from modules.fire.schema import filter_fire_calls
from modules.session_state import DEFAULTS


def test_general_mode_is_default_and_fire_mode_is_explicit():
    defaults = fire_session_defaults()

    assert defaults["mode"] == GENERAL_MODE
    assert GENERAL_MODE != FIRE_EMS_MODE
    assert defaults["fire_enabled"] is False


def test_fire_classifier_retains_original_type_and_classifies_structure_fire():
    result = classify_call("Structure Fire - Working")

    assert result.category == "structure_fire"
    assert result.original_type == "Structure Fire - Working"
    assert result.confidence == "high"
    assert result.rule_id == "structure_fire"


def test_dataframe_classification_preserves_original_incident_type():
    calls = pd.DataFrame(
        {
            "incident_type": ["EMS Difficulty Breathing", "Traffic Collision", "Unknown"],
            "agency": ["medical", "fire", "police"],
        }
    )

    classified = classify_calls(calls)

    assert classified["incident_type"].tolist() == calls["incident_type"].tolist()
    assert classified["fire_category"].tolist() == ["medical", "mva", "other"]
    assert "fire_classification_rule" in classified.columns


def test_fire_dataset_detection_only_recommends_mode():
    calls = pd.DataFrame({"incident_type": ["Structure Fire", "EMS Chest Pain", "Traffic Collision"]})

    assert recommend_fire_mode(calls) is True


def test_fire_filter_returns_selected_categories_without_mutating_input():
    calls = pd.DataFrame(
        {
            "incident_type": ["Structure Fire", "Chest Pain", "Traffic Collision"],
            "fire_category": ["structure_fire", "medical", "mva"],
        }
    )

    filtered = filter_fire_calls(calls, {"structure_fire", "mva"})

    assert filtered["incident_type"].tolist() == ["Structure Fire", "Traffic Collision"]
    assert calls["incident_type"].tolist() == ["Structure Fire", "Chest Pain", "Traffic Collision"]


def test_fire_session_payload_is_versioned_and_additive():
    merged = merge_fire_session({"mode": FIRE_EMS_MODE, "fire_enabled": True})

    assert merged["version"] == FIRE_SESSION_VERSION
    assert merged["mode"] == FIRE_EMS_MODE
    assert merged["fire_enabled"] is True
    assert merged["category_filter"] == []


def test_streamlit_session_defaults_keep_general_mode_and_fire_gate_off():
    assert DEFAULTS["app_mode"] == GENERAL_MODE
    assert DEFAULTS["fire_feature_gate"] is False
    assert DEFAULTS["fire_category_filter"] == []
