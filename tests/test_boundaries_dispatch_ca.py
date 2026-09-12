import modules.boundaries as boundaries


def test_fetch_county_boundary_local_routes_to_ca_for_province_abbr(monkeypatch):
    calls = {}

    def _fake_fetch_cd(province_abbr, name):
        calls['args'] = (province_abbr, name)
        return True, "fake-cd-gdf"

    monkeypatch.setattr(boundaries, "fetch_cd_boundary_local", _fake_fetch_cd)
    assert boundaries.fetch_county_boundary_local("ON", "Waterloo") == (True, "fake-cd-gdf")
    assert calls['args'] == ("ON", "Waterloo")


def test_fetch_place_boundary_local_routes_to_ca_for_province_abbr(monkeypatch):
    monkeypatch.setattr(boundaries, "fetch_csd_boundary_local", lambda p, n: (True, "fake-csd-gdf"))
    assert boundaries.fetch_place_boundary_local("AB", "Calgary") == (True, "fake-csd-gdf")


def test_fetch_county_by_centroid_routes_to_ca_for_province_abbr(monkeypatch):
    monkeypatch.setattr(boundaries, "fetch_cd_by_centroid", lambda df, p: (True, "fake-cd-centroid-gdf"))
    assert boundaries.fetch_county_by_centroid(None, "BC") == (True, "fake-cd-centroid-gdf")


def test_lookup_zip_code_routes_to_ca_postal_lookup(monkeypatch):
    monkeypatch.setattr(boundaries, "lookup_postal_code_ca", lambda code: ("Toronto", "ON", "Ontario"))
    assert boundaries.lookup_zip_code("M5V 2T6") == ("Toronto", "ON", "Ontario")


def test_lookup_population_for_boundary_routes_to_ca(monkeypatch):
    monkeypatch.setattr(boundaries, "fetch_ca_population", lambda p, n, boundary_kind='place': 12345)
    assert boundaries._lookup_population_for_boundary("QC", "Montreal", boundary_kind='place') == 12345


def test_us_paths_are_unaffected_for_us_state_abbr(monkeypatch):
    # Sanity check: a US state abbreviation must never reach the CA functions.
    def _fail(*a, **k):
        raise AssertionError("US state routed to a CA function")

    monkeypatch.setattr(boundaries, "fetch_cd_boundary_local", _fail)
    monkeypatch.setattr(boundaries, "fetch_csd_boundary_local", _fail)
    monkeypatch.setattr(boundaries, "fetch_cd_by_centroid", _fail)
    monkeypatch.setattr(boundaries, "fetch_ca_population", _fail)
    # These will still return False/None (no real data loaded for a fake county),
    # the point is only that they don't raise via the CA branch.
    boundaries.fetch_county_boundary_local("NY", "Erie")
    boundaries.fetch_place_boundary_local("NY", "Buffalo")
    boundaries.fetch_county_by_centroid(None, "NY")
    boundaries._lookup_population_for_boundary("NY", "Buffalo", boundary_kind='place')
