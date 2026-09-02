import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from modules.stations import _filter_station_candidates_to_boundary


def test_filter_station_candidates_to_boundary_keeps_only_points_inside():
    df_stations = pd.DataFrame(
        [
            {"name": "Inside", "lat": 0.5, "lon": 0.5},
            {"name": "Outside", "lat": 1.5, "lon": 1.5},
        ]
    )
    boundary = Polygon([(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)])

    filtered = _filter_station_candidates_to_boundary(df_stations, boundary, 4326)

    assert list(filtered["name"]) == ["Inside"]
    assert filtered.iloc[0]["lat"] == 0.5
    assert filtered.iloc[0]["lon"] == 0.5


def test_filter_station_candidates_to_boundary_returns_empty_frame_for_empty_input():
    boundary = gpd.GeoSeries([Polygon([(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)])], crs="EPSG:4326").iloc[0]

    filtered = _filter_station_candidates_to_boundary(pd.DataFrame(), boundary, 4326)

    assert filtered.empty
