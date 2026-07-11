import pandas as pd

from modules.dashboard_helpers import (
    _suggestion_widget_key,
    deployed_station_indices,
    sync_station_suggestion_modes,
)


def _suggestions(count=5):
    return [
        {
            "station_idx": i,
            "rank": i + 1,
            "role": "Guardian" if i == 0 else "Responder",
            "name": f"Station {i + 1}",
        }
        for i in range(count)
    ]


def _counts(modes):
    return {
        "guardian": sum(1 for mode in modes.values() if mode == "Guardian"),
        "responder": sum(1 for mode in modes.values() if mode == "Responder"),
        "off": sum(1 for mode in modes.values() if mode == "Off"),
    }


def test_slider_assigns_ranked_station_suggestions():
    session_state = {"_station_suggestion_rank_by": "call"}

    modes = sync_station_suggestion_modes(
        session_state,
        _suggestions(),
        k_guardian=1,
        k_responder=2,
    )

    assert _counts(modes) == {"guardian": 1, "responder": 2, "off": 2}
    assert modes[0] == "Guardian"
    assert modes[1] == "Responder"
    assert modes[2] == "Responder"


def test_card_toggle_to_responder_queues_slider_count():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Off", 3: "Off", 4: "Off"},
    }
    session_state[_suggestion_widget_key(session_state, 2)] = "Responder"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=1,
    )

    assert modes[2] == "Responder"
    assert session_state["_pending_k_resp"] == 2
    assert session_state["_pending_k_guard"] == 1


def test_card_toggle_to_off_queues_slider_count():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Responder", 3: "Off", 4: "Off"},
    }
    session_state[_suggestion_widget_key(session_state, 2)] = "Off"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=2,
    )

    assert modes[2] == "Off"
    assert session_state["_pending_k_resp"] == 1
    assert session_state["_pending_k_guard"] == 1


def test_card_role_change_queues_both_slider_counts():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Off", 3: "Off", 4: "Off"},
    }
    session_state[_suggestion_widget_key(session_state, 0)] = "Responder"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=1,
    )

    assert modes[0] == "Responder"
    assert session_state["_pending_k_resp"] == 2
    assert session_state["_pending_k_guard"] == 0


def test_slider_change_rebuilds_manual_card_modes():
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Off", 1: "Responder", 2: "Off", 3: "Responder", 4: "Off"},
        "_suggestion_apply_fleet_counts": True,
    }

    modes = sync_station_suggestion_modes(
        session_state,
        _suggestions(),
        k_guardian=2,
        k_responder=1,
    )

    assert _counts(modes) == {"guardian": 2, "responder": 1, "off": 2}
    assert modes[0] == "Guardian"
    assert modes[1] == "Guardian"
    assert modes[2] == "Responder"


def test_forced_custom_suggestion_mode_is_respected():
    suggestions = _suggestions(4) + [
        {
            "station_idx": 9,
            "rank": 5,
            "role": "Responder",
            "name": "[Police] Custom 1",
        }
    ]
    session_state = {
        "_station_suggestion_rank_by": "call",
        "custom_stations": pd.DataFrame(
            [{"name": "Custom 1", "type": "Police", "lock_role": "Guardian"}]
        ),
        "pinned_guard_names": ["[Police] Custom 1"],
        "pinned_resp_names": [],
        "_suggestion_apply_fleet_counts": True,
    }

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=0,
        k_responder=1,
    )

    assert modes[9] == "Guardian"
    assert _counts(modes) == {"guardian": 1, "responder": 1, "off": 3}


def test_deployed_station_indices_normalizes_active_drone_indices():
    assert deployed_station_indices(
        [
            {"idx": 2, "type": "RESPONDER"},
            {"idx": "4", "type": "GUARDIAN"},
            {"idx": None, "type": "RESPONDER"},
            {"idx": "bad", "type": "GUARDIAN"},
            object(),
        ]
    ) == {2, 4}
