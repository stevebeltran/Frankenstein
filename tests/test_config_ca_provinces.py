# tests/test_config_ca_provinces.py
from modules.config import PROVINCE_FIPS, CA_PROVINCES_ABBR, STATE_FIPS


def test_province_fips_covers_all_thirteen_provinces_and_territories():
    assert len(PROVINCE_FIPS) == 13
    assert PROVINCE_FIPS["ON"] == "35"
    assert PROVINCE_FIPS["BC"] == "59"


def test_province_abbreviations_do_not_collide_with_us_state_abbreviations():
    assert not (set(PROVINCE_FIPS) & set(STATE_FIPS))


def test_ca_provinces_abbr_maps_full_name_to_code_present_in_province_fips():
    for full_name, abbr in CA_PROVINCES_ABBR.items():
        assert abbr in PROVINCE_FIPS
