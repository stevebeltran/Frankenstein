import geopandas as gpd
from shapely.geometry import Point

import modules.dashboard_helpers as dashboard_helpers


def test_nested_jurisdictions_show_independent_call_shares():
    boundaries = gpd.GeoDataFrame(
        {
            "DISPLAY_NAME": ["Raleigh", "Wake County"],
            "data_count": [4903, 4999],
            "call_share": [0.9806, 0.9998],
        },
        geometry=[Point(-78.64, 35.78), Point(-78.64, 35.78)],
        crs="EPSG:4326",
    )

    labeled = dashboard_helpers.build_jurisdiction_option_labels(boundaries)

    assert labeled["LABEL"].tolist() == [
        "Raleigh (98.1% of calls)",
        "Wake County (100.0% of calls)",
    ]


def test_legacy_jurisdictions_keep_normalized_compatibility_labels():
    boundaries = gpd.GeoDataFrame(
        {
            "DISPLAY_NAME": ["North", "South"],
            "data_count": [3, 1],
        },
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )

    labeled = dashboard_helpers.build_jurisdiction_option_labels(boundaries)

    assert labeled["LABEL"].tolist() == [
        "North (75.0% of calls)",
        "South (25.0% of calls)",
    ]
