from modules.dashboard_helpers import assign_station_colors

GUARDIAN_COLOR = "#FFD700"
RESPONDER_COLOR = "#00D2FF"
EXTRA_COLORS = ["#FF6B6B", "#4ECDC4", "#A78BFA", "#F97316"]


def test_first_guardian_and_responder_get_role_colors():
    session_state = {}
    color_map = assign_station_colors(
        session_state,
        [(3, "GUARDIAN"), (7, "RESPONDER")],
        GUARDIAN_COLOR,
        RESPONDER_COLOR,
        EXTRA_COLORS,
    )
    assert color_map["3_GUARDIAN"] == GUARDIAN_COLOR
    assert color_map["7_RESPONDER"] == RESPONDER_COLOR


def test_existing_station_keeps_color_when_new_guardian_toggled_on():
    session_state = {}
    first = assign_station_colors(
        session_state,
        [(3, "GUARDIAN"), (7, "GUARDIAN")],
        GUARDIAN_COLOR,
        RESPONDER_COLOR,
        EXTRA_COLORS,
    )
    # New guardian appears EARLIER in deployment order — old colors must not shift.
    second = assign_station_colors(
        session_state,
        [(1, "GUARDIAN"), (3, "GUARDIAN"), (7, "GUARDIAN")],
        GUARDIAN_COLOR,
        RESPONDER_COLOR,
        EXTRA_COLORS,
    )
    assert second["3_GUARDIAN"] == first["3_GUARDIAN"]
    assert second["7_GUARDIAN"] == first["7_GUARDIAN"]
    assert second["1_GUARDIAN"] not in {second["3_GUARDIAN"], second["7_GUARDIAN"]}


def test_toggled_off_station_releases_its_color():
    session_state = {}
    assign_station_colors(
        session_state,
        [(3, "GUARDIAN"), (7, "GUARDIAN")],
        GUARDIAN_COLOR,
        RESPONDER_COLOR,
        EXTRA_COLORS,
    )
    released = session_state["station_color_assignments"]["7_GUARDIAN"]
    # Station 7 off → its color freed for the next new station.
    color_map = assign_station_colors(
        session_state,
        [(3, "GUARDIAN"), (9, "GUARDIAN")],
        GUARDIAN_COLOR,
        RESPONDER_COLOR,
        EXTRA_COLORS,
    )
    assert "7_GUARDIAN" not in session_state["station_color_assignments"]
    assert color_map["9_GUARDIAN"] == released


def test_colors_unique_until_palette_exhausted():
    session_state = {}
    deployments = [(i, "GUARDIAN") for i in range(6)]
    color_map = assign_station_colors(
        session_state,
        deployments,
        GUARDIAN_COLOR,
        RESPONDER_COLOR,
        EXTRA_COLORS,
    )
    # 1 role color + 4 extras = 5 unique; 6th wraps.
    assert len(set(list(color_map.values())[:5])) == 5


def test_same_station_same_role_stable_across_reruns():
    session_state = {}
    deployments = [(2, "RESPONDER"), (5, "GUARDIAN"), (8, "RESPONDER")]
    first = assign_station_colors(
        session_state, deployments, GUARDIAN_COLOR, RESPONDER_COLOR, EXTRA_COLORS
    )
    second = assign_station_colors(
        session_state, deployments, GUARDIAN_COLOR, RESPONDER_COLOR, EXTRA_COLORS
    )
    assert first == second
