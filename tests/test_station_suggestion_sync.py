import pandas as pd

from modules.dashboard_helpers import (
    _suggestion_widget_key,
    apply_manual_suggestion_deployments,
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


def test_card_toggle_to_responder_records_manual_mode_and_increments_slider_count():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Off", 3: "Off", 4: "Off"},
    }
    session_state[_suggestion_widget_key(session_state, 2, suggestions[2])] = "Responder"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=1,
    )

    assert modes[2] == "Responder"
    assert session_state["_pending_k_resp"] == 2
    assert "_pending_k_guard" not in session_state
    assert session_state["_suggestion_manual_modes"] == {2: "Responder"}


def test_card_toggle_to_guardian_records_manual_mode_and_increments_slider_count():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Off", 3: "Off", 4: "Off"},
    }
    session_state[_suggestion_widget_key(session_state, 2, suggestions[2])] = "Guardian"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=1,
    )

    assert modes[2] == "Guardian"
    assert "_pending_k_resp" not in session_state
    assert session_state["_pending_k_guard"] == 2
    assert session_state["_suggestion_manual_modes"] == {2: "Guardian"}


def test_card_toggle_to_off_records_manual_mode_and_decrements_slider_count():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Responder", 3: "Off", 4: "Off"},
    }
    session_state[_suggestion_widget_key(session_state, 2, suggestions[2])] = "Off"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=2,
    )

    assert modes[2] == "Off"
    assert session_state["_pending_k_resp"] == 1
    assert "_pending_k_guard" not in session_state
    assert session_state["_suggestion_manual_modes"] == {2: "Off"}


def test_card_role_change_records_manual_mode_and_updates_slider_counts():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Off", 3: "Off", 4: "Off"},
    }
    session_state[_suggestion_widget_key(session_state, 0, suggestions[0])] = "Responder"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=1,
    )

    assert modes[0] == "Responder"
    assert session_state["_pending_k_resp"] == 2
    assert session_state["_pending_k_guard"] == 0
    assert session_state["_suggestion_manual_modes"] == {0: "Responder"}


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


def test_manual_suggestion_deployments_override_optimizer_indices():
    station_metadata = [{"name": f"Station {i}"} for i in range(5)]

    resp_idx, guard_idx = apply_manual_suggestion_deployments(
        station_metadata,
        active_resp_idx=[1, 2],
        active_guard_idx=[0],
        manual_modes={0: "Responder", 2: "Off", 3: "Guardian"},
    )

    assert resp_idx == [1, 0]
    assert guard_idx == [3]


def test_manual_suggestion_deployments_force_lower_card_without_extra_ring():
    station_metadata = [{"name": f"Station {i}"} for i in range(30)]

    resp_idx, guard_idx = apply_manual_suggestion_deployments(
        station_metadata,
        active_resp_idx=[1, 2, 3],
        active_guard_idx=[0],
        manual_modes={26: "Responder"},
        target_resp_count=3,
        target_guard_count=1,
    )

    assert 26 in resp_idx
    assert len(resp_idx) == 3
    assert len(guard_idx) == 1
    assert 26 not in guard_idx


def test_lower_rank_widget_key_updates_exact_station_not_next_card():
    suggestions = _suggestions(30)
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {s["station_idx"]: "Off" for s in suggestions},
    }
    session_state[_suggestion_widget_key(session_state, 26, suggestions[26])] = "Responder"

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=0,
        k_responder=0,
    )

    assert modes[26] == "Responder"
    assert modes[27] == "Off"
    assert session_state["_suggestion_manual_modes"] == {26: "Responder"}
