import pandas as pd

from modules.dashboard_helpers import (
    _suggestion_widget_key,
    apply_suggestion_widget_overrides,
    apply_manual_suggestion_deployments,
    deployed_station_indices,
    reconcile_suggestion_modes_from_deployments,
    reconcile_unique_deployment_indices,
    sort_uploaded_station_suggestions,
    sync_uploaded_station_fleet_counts,
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


def _set_card_mode(session_state, idx, suggestion, mode):
    """Simulate a user clicking the Guardian/Responder checkboxes on a card."""
    widget_key = _suggestion_widget_key(session_state, idx, suggestion)
    session_state[f"{widget_key}_g"] = mode in ("Guardian", "Both")
    session_state[f"{widget_key}_r"] = mode in ("Responder", "Both")


def _counts(modes):
    return {
        "guardian": sum(1 for mode in modes.values() if mode == "Guardian"),
        "responder": sum(1 for mode in modes.values() if mode == "Responder"),
        "off": sum(1 for mode in modes.values() if mode == "Off"),
    }


def test_stations_uploaded_defaults_all_cards_to_responder():
    session_state = {"_station_suggestion_rank_by": "call"}

    modes = sync_station_suggestion_modes(
        session_state,
        _suggestions(),
        k_guardian=1,
        k_responder=2,
        stations_uploaded=True,
    )

    assert set(modes.values()) == {"Responder"}


def test_uploaded_station_counts_follow_all_active_cards():
    session_state = {
        "stations_user_uploaded": True,
        "suggestion_modes": {0: "Responder", 1: "Responder", 2: "Responder", 3: "Responder", 4: "Responder"},
    }

    changed = sync_uploaded_station_fleet_counts(session_state, current_k_guardian=1, current_k_responder=2)

    assert changed is True
    assert session_state["_pending_k_resp"] == 5
    assert session_state["_pending_k_guard"] == 0
    # Must NOT set _suggestion_apply_fleet_counts: that flag tells
    # sync_station_suggestion_modes to re-rank cards from budget via
    # _ranked_suggestion_modes, which has no concept of 'Both' and would
    # silently collapse a user's Guardian+Responder card selection back to
    # a single role on the very next rerun. That flag is reserved for real
    # slider drags (see the sidebar slider-change handler).
    assert "_suggestion_apply_fleet_counts" not in session_state


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
    _set_card_mode(session_state, 2, suggestions[2], "Responder")

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=1,
    )

    assert modes[2] == "Responder"
    assert session_state["_pending_k_resp"] == 2
    assert session_state["_pending_k_guard"] == 1
    assert session_state["_suggestion_manual_modes"] == {2: "Responder"}


def test_card_toggle_to_guardian_records_manual_mode_and_increments_slider_count():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Off", 3: "Off", 4: "Off"},
    }
    _set_card_mode(session_state, 2, suggestions[2], "Guardian")

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=1,
    )

    assert modes[2] == "Guardian"
    assert session_state["_pending_k_resp"] == 1
    assert session_state["_pending_k_guard"] == 2
    assert session_state["_suggestion_manual_modes"] == {2: "Guardian"}


def test_card_toggle_to_off_records_manual_mode_and_decrements_slider_count():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Responder", 3: "Off", 4: "Off"},
    }
    _set_card_mode(session_state, 2, suggestions[2], "Off")

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=2,
    )

    assert modes[2] == "Off"
    assert session_state["_pending_k_resp"] == 1
    assert session_state["_pending_k_guard"] == 1
    assert session_state["_suggestion_manual_modes"] == {2: "Off"}


def test_card_role_change_records_manual_mode_and_updates_slider_counts():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Off", 3: "Off", 4: "Off"},
    }
    _set_card_mode(session_state, 0, suggestions[0], "Responder")

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


def test_card_role_switch_uses_exact_card_counts_not_delta_guess():
    suggestions = _suggestions()
    session_state = {
        "_station_suggestion_rank_by": "call",
        "suggestion_modes": {0: "Guardian", 1: "Responder", 2: "Responder", 3: "Off", 4: "Off"},
    }
    _set_card_mode(session_state, 2, suggestions[2], "Guardian")

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=1,
        k_responder=2,
    )

    assert modes[2] == "Guardian"
    assert session_state["_pending_k_resp"] == 1
    assert session_state["_pending_k_guard"] == 2
    assert session_state["_suggestion_manual_modes"] == {2: "Guardian"}


def test_apply_suggestion_widget_overrides_updates_counts_before_optimizer():
    suggestions = _suggestions(10)
    modes = {0: "Responder", 7: "Responder", 8: "Responder", 9: "Guardian"}
    session_state = {
        "_suggestion_widget_version": 0,
        "suggestion_modes": dict(modes),
    }
    _set_card_mode(session_state, 8, suggestions[8], "Guardian")

    updated = apply_suggestion_widget_overrides(session_state, suggestions, modes)

    assert updated[8] == "Guardian"
    assert session_state["_pending_k_resp"] == 2
    assert session_state["_pending_k_guard"] == 2
    assert session_state["_suggestion_sync_source"] == "cards"


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


def test_manual_suggestion_deployments_both_mode_deploys_to_both_roles():
    station_metadata = [{"name": f"Station {i}"} for i in range(5)]

    resp_idx, guard_idx = apply_manual_suggestion_deployments(
        station_metadata,
        active_resp_idx=[],
        active_guard_idx=[],
        manual_modes={2: "Both"},
        target_resp_count=1,
        target_guard_count=1,
    )

    assert 2 in resp_idx
    assert 2 in guard_idx


def test_reconcile_unique_deployment_indices_keeps_both_preferred_station_in_both_roles():
    station_metadata = [{"name": f"Station {i}"} for i in range(5)]

    resp_idx, guard_idx = reconcile_unique_deployment_indices(
        station_metadata,
        active_resp_idx=[1],
        active_guard_idx=[1],
        suggestions=_suggestions(5),
        target_resp_count=1,
        target_guard_count=1,
        preferred_modes={1: "Both"},
    )

    assert resp_idx == [1]
    assert guard_idx == [1]


def test_reconcile_suggestion_modes_reports_both_when_deployed_as_both_roles():
    session_state = {
        "suggestion_modes": {0: "Off", 1: "Off"},
        "suggestion_toggles": {0: False, 1: False},
    }

    modes = reconcile_suggestion_modes_from_deployments(
        session_state,
        _suggestions(2),
        active_resp_idx=[1],
        active_guard_idx=[1],
    )

    assert modes[1] == "Both"
    assert session_state["_suggestion_selected_resp_count"] == 1
    assert session_state["_suggestion_selected_guard_count"] == 1


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
    _set_card_mode(session_state, 26, suggestions[26], "Responder")

    modes = sync_station_suggestion_modes(
        session_state,
        suggestions,
        k_guardian=0,
        k_responder=0,
    )

    assert modes[26] == "Responder"
    assert modes[27] == "Off"
    assert session_state["_suggestion_manual_modes"] == {26: "Responder"}


def test_reconcile_suggestion_modes_reflects_final_optimizer_deployments():
    session_state = {
        "suggestion_modes": {0: "Guardian", 1: "Guardian", 2: "Off", 3: "Off"},
        "suggestion_toggles": {0: True, 1: True, 2: False, 3: False},
    }

    modes = reconcile_suggestion_modes_from_deployments(
        session_state,
        _suggestions(4),
        active_resp_idx=[3],
        active_guard_idx=[1, 2],
    )

    assert modes == {0: "Off", 1: "Guardian", 2: "Guardian", 3: "Responder"}
    assert session_state["suggestion_toggles"] == {0: False, 1: True, 2: True, 3: True}
    assert session_state["_suggestion_selected_resp_count"] == 1
    assert session_state["_suggestion_selected_guard_count"] == 2
    assert session_state[_suggestion_widget_key(session_state, 0, _suggestions(4)[0])] == "Off"
    assert session_state[_suggestion_widget_key(session_state, 1, _suggestions(4)[1])] == "Guardian"
    assert session_state[_suggestion_widget_key(session_state, 2, _suggestions(4)[2])] == "Guardian"
    assert session_state[_suggestion_widget_key(session_state, 3, _suggestions(4)[3])] == "Responder"


def test_reconcile_unique_deployment_indices_fills_duplicate_role_station():
    station_metadata = [{"name": f"Station {i}"} for i in range(5)]
    suggestions = _suggestions(5)

    resp_idx, guard_idx = reconcile_unique_deployment_indices(
        station_metadata,
        active_resp_idx=[1, 2],
        active_guard_idx=[1],
        suggestions=suggestions,
        target_resp_count=2,
        target_guard_count=1,
    )

    assert len(resp_idx) == 2
    assert len(guard_idx) == 1
    assert not (set(resp_idx) & set(guard_idx))
    assert 1 in guard_idx


def test_reconcile_unique_deployment_indices_respects_manual_role_preference():
    station_metadata = [{"name": f"Station {i}"} for i in range(5)]

    resp_idx, guard_idx = reconcile_unique_deployment_indices(
        station_metadata,
        active_resp_idx=[1],
        active_guard_idx=[1, 2],
        suggestions=_suggestions(5),
        target_resp_count=1,
        target_guard_count=2,
        preferred_modes={1: "Responder"},
    )

    assert 1 in resp_idx
    assert 1 not in guard_idx
    assert len(resp_idx) == 1
    assert len(guard_idx) == 2


def _upload_suggestion(idx, call_r, call_g, land_r, land_g, marginal=0):
    return {
        "station_idx": idx,
        "rank": idx + 1,
        "role": "Responder",
        "name": f"Station {idx}",
        "call_pct": call_r,
        "call_pct_responder": call_r,
        "call_pct_guardian": call_g,
        "land_pct": land_r,
        "land_pct_responder": land_r,
        "land_pct_guardian": land_g,
        "marginal_calls": marginal,
    }


def test_sort_uploaded_orders_guardian_cards_by_guardian_land_pct():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=50, land_g=5),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=5, land_g=40),
        _upload_suggestion(2, call_r=10, call_g=10, land_r=30, land_g=60),
    ]
    modes = {0: "Guardian", 1: "Guardian", 2: "Guardian"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="land", resp_rank_by="call"
    )

    assert [s["station_idx"] for s in ordered] == [2, 1, 0]
    assert [s["rank"] for s in ordered] == [1, 2, 3]


def test_sort_uploaded_orders_responder_cards_by_responder_land_pct():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=50, land_g=5),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=5, land_g=40),
        _upload_suggestion(2, call_r=10, call_g=10, land_r=30, land_g=60),
    ]
    modes = {0: "Responder", 1: "Responder", 2: "Responder"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="call", resp_rank_by="land"
    )

    assert [s["station_idx"] for s in ordered] == [0, 2, 1]


def test_sort_uploaded_uses_each_cards_own_assigned_role():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=90, land_g=10),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=10, land_g=90),
    ]
    modes = {0: "Responder", 1: "Guardian"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="land", resp_rank_by="land"
    )

    assert [s["station_idx"] for s in ordered] == [0, 1]
    assert ordered[0]["land_pct_responder"] == 90
    assert ordered[1]["land_pct_guardian"] == 90


def test_sort_uploaded_off_cards_fall_back_to_responder_metric():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=20, land_g=99),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=80, land_g=1),
    ]
    modes = {0: "Off", 1: "Off"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="land", resp_rank_by="land"
    )

    assert [s["station_idx"] for s in ordered] == [1, 0]


def test_sort_uploaded_defaults_unknown_rank_by_to_call():
    suggestions = [
        _upload_suggestion(0, call_r=5, call_g=5, land_r=99, land_g=99),
        _upload_suggestion(1, call_r=50, call_g=50, land_r=1, land_g=1),
    ]
    modes = {0: "Responder", 1: "Responder"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="bogus", resp_rank_by="bogus"
    )

    assert [s["station_idx"] for s in ordered] == [1, 0]


def test_sort_uploaded_does_not_mutate_input_list():
    suggestions = [_upload_suggestion(0, 10, 10, 10, 10)]
    original_rank = suggestions[0]["rank"]

    sort_uploaded_station_suggestions(suggestions, {0: "Responder"}, resp_rank_by="land")

    assert suggestions[0]["rank"] == original_rank
