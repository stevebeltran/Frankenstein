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


def test_build_demo_boundaries_falls_back_to_tiger_for_unincorporated_cdp():
    # Edwards, CO is an unincorporated Census-designated place with no matching
    # county name — places_lite.parquet only carries incorporated cities/towns,
    # so both local lookups miss and the fix must reach for a live TIGER lookup.
    import geopandas as gpd
    from shapely.geometry import Point

    def no_local_boundary(*_args, **_kwargs):
        return False, None

    def no_population(*_args, **_kwargs):
        return 0

    def no_save(*_args, **_kwargs):
        return ""

    tiger_gdf = gpd.GeoDataFrame({"NAME": ["Edwards"]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    tiger_calls = []

    def fake_tiger_city(state_fips, city_name, output_dir):
        tiger_calls.append((state_fips, city_name, output_dir))
        return True, tiger_gdf

    all_gdfs, _records, _pop, _messages, warnings, _rerun, _verified = build_demo_boundaries(
        {},
        [{"city": "Edwards", "state": "CO"}],
        {"CO": "08"},
        {},
        [],
        no_local_boundary,
        no_local_boundary,
        no_local_boundary,
        no_save,
        no_population,
        no_population,
        fetch_tiger_city_shapefile=fake_tiger_city,
    )

    assert warnings == []
    assert len(all_gdfs) == 1
    assert tiger_calls == [("08", "Edwards", "jurisdiction_data")]
    assert any(
        "Edwards not found in local boundary data" in msg and "TIGER fallback" in msg
        for msg in _messages
    )
