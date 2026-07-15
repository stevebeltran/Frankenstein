from modules.boundaries import suggest_boundary_matches
from modules.onboarding import build_demo_boundaries


def test_boundary_suggestions_use_parquet_places_and_counties_for_misspelled_city():
    suggestions = suggest_boundary_matches("NC", "Ashville")
    display_names = [item["display_name"] for item in suggestions]

    assert display_names[0] == "Asheville, NC"
    assert "Buncombe County, NC" in display_names


def test_build_demo_boundaries_includes_close_match_prompt_on_failure():
    def no_boundary(*_args, **_kwargs):
        return False, None

    def no_population(*_args, **_kwargs):
        return 0

    def no_save(*_args, **_kwargs):
        return ""

    all_gdfs, _records, _pop, _messages, warnings, _rerun, _verified = build_demo_boundaries(
        {},
        [{"city": "Ashville", "state": "NC"}],
        {"NC": "37"},
        {},
        [],
        no_boundary,
        no_boundary,
        no_boundary,
        no_save,
        no_population,
        no_population,
        suggest_boundary_matches=lambda _state, _city: [
            {"kind": "place", "display_name": "Asheville, NC"},
            {"kind": "county", "display_name": "Buncombe County, NC"},
        ],
    )

    assert all_gdfs == []
    assert "Could not find a boundary for Ashville, NC." in warnings[0]
    assert "Did you mean Asheville, NC?" in warnings[0]
    assert "County option: Buncombe County, NC." in warnings[0]
    assert _verified is False
