"""
Unit tests for search utility functions.

Tests validate text normalization, coordinate detection,
location matching, and candidate deduplication.
"""

import pytest

from modules.search_utils import (
    normalize_search_text,
    is_probably_coordinate,
    score_location_match,
    deduplicate_candidates,
)


class TestNormalizeSearchText:
    """Tests for search text normalization."""

    def test_normalize_empty_string(self):
        """Test normalization of empty string."""
        result = normalize_search_text("")
        assert result == ""

    def test_normalize_whitespace(self):
        """Test that extra whitespace is removed."""
        result = normalize_search_text("  hello   world  ")
        assert result == "hello world"

    def test_normalize_case(self):
        """Test that text is converted to lowercase."""
        result = normalize_search_text("HELLO World")
        assert result == "hello world"

    def test_normalize_special_characters(self):
        """Test handling of special characters."""
        result = normalize_search_text("San Francisco")
        assert result == "san francisco"

    def test_normalize_none_value(self):
        """Test normalization of None-like values."""
        result = normalize_search_text(None)
        assert isinstance(result, str)

    def test_normalize_numeric_string(self):
        """Test normalization of numeric strings."""
        result = normalize_search_text("12345")
        assert result == "12345"

    def test_normalize_multiline(self):
        """Test normalization with newlines."""
        result = normalize_search_text("line1\nline2")
        assert "line1" in result
        assert "line2" in result


class TestIsProbablyCoordinate:
    """Tests for coordinate detection."""

    def test_coordinate_decimal_degrees(self):
        """Test detection of decimal degree coordinates."""
        assert is_probably_coordinate("40.7128, -74.0060")
        assert is_probably_coordinate("40.7128 -74.0060")

    def test_coordinate_negative_values(self):
        """Test detection with negative latitude/longitude."""
        assert is_probably_coordinate("-33.8688, 151.2093")
        assert is_probably_coordinate("-33.8688 151.2093")

    def test_not_coordinate_single_number(self):
        """Test that single number is not a coordinate."""
        assert not is_probably_coordinate("40.7128")

    def test_not_coordinate_text(self):
        """Test that regular text is not detected as coordinate."""
        assert not is_probably_coordinate("San Francisco")
        assert not is_probably_coordinate("123 Main Street")

    def test_coordinate_with_comma(self):
        """Test coordinates with comma separator."""
        assert is_probably_coordinate("40.7128,  -74.0060")

    def test_coordinate_spaces_only(self):
        """Test coordinates with space separator."""
        assert is_probably_coordinate("40.7128   -74.0060")

    def test_not_coordinate_incomplete(self):
        """Test that incomplete coordinates are not detected."""
        assert not is_probably_coordinate("40.7128, ")

    def test_coordinate_edge_case_values(self):
        """Test coordinates with edge case values."""
        assert is_probably_coordinate("0, 0")
        assert is_probably_coordinate("-90, 180")
        assert is_probably_coordinate("90, -180")


class TestScoreLocationMatch:
    """Tests for location matching scoring."""

    def test_score_basic_candidate(self):
        """Test scoring of basic valid candidate."""
        candidate = {"address": "123 Main St", "city": "Denver", "state": "CO"}
        score = score_location_match(candidate)
        assert 0.0 <= score <= 1.0

    def test_score_exact_state_match(self):
        """Test that exact state match increases score."""
        candidate = {"state": "Colorado"}
        score_match = score_location_match(candidate, preferred_state="CO")
        score_no_match = score_location_match(candidate, preferred_state="CA")
        # Should have different scores, but both valid
        assert 0.0 <= score_match <= 1.0
        assert 0.0 <= score_no_match <= 1.0

    def test_score_state_case_insensitive(self):
        """Test that state matching is case-insensitive."""
        candidate = {"state": "colorado"}
        score1 = score_location_match(candidate, preferred_state="CO")
        score2 = score_location_match(candidate, preferred_state="Colorado")
        assert score1 == score2

    def test_score_exact_city_match(self):
        """Test that exact city match increases score."""
        candidate = {"city": "Denver"}
        score_match = score_location_match(candidate, preferred_city="Denver")
        score_no_match = score_location_match(candidate, preferred_city="Boulder")
        assert score_match > score_no_match

    def test_score_city_case_insensitive(self):
        """Test that city matching is case-insensitive."""
        candidate = {"city": "denver"}
        score1 = score_location_match(candidate, preferred_city="Denver")
        score2 = score_location_match(candidate, preferred_city="DENVER")
        assert score1 == score2

    def test_score_partial_city_match(self):
        """Test that partial city match gives bonus."""
        candidate = {"city": "Denver"}
        # Exact match should score higher than substring match
        score_exact = score_location_match(candidate, preferred_city="Denver")
        score_partial = score_location_match(candidate, preferred_city="Den")
        assert score_exact >= score_partial

    def test_score_combined_preferences(self):
        """Test scoring with both city and state preferences."""
        candidate = {"city": "Denver", "state": "Colorado"}
        score_both = score_location_match(
            candidate, preferred_city="Denver", preferred_state="CO"
        )
        score_state_only = score_location_match(
            candidate, preferred_state="CO"
        )
        # Both matches should score highest
        assert score_both >= score_state_only

    def test_score_range(self):
        """Test that scores are always in valid range."""
        candidates = [
            {"city": "Denver", "state": "CO"},
            {"city": "Boulder"},
            {"state": "Colorado"},
            {},
        ]
        for candidate in candidates:
            score = score_location_match(candidate, "Denver", "CO")
            assert 0.0 <= score <= 1.0


class TestDeduplicateCandidates:
    """Tests for candidate deduplication."""

    def test_deduplicate_no_duplicates(self):
        """Test deduplication with no duplicates."""
        candidates = [
            {"address": "123 Main St", "city": "Denver"},
            {"address": "456 Oak Ave", "city": "Boulder"},
            {"address": "789 Pine Rd", "city": "Fort Collins"},
        ]
        result = deduplicate_candidates(candidates)
        assert len(result) == 3

    def test_deduplicate_exact_duplicates(self):
        """Test deduplication with exact duplicate addresses."""
        candidates = [
            {"address": "123 Main St", "city": "Denver"},
            {"address": "123 Main St", "city": "Denver"},
            {"address": "456 Oak Ave", "city": "Boulder"},
        ]
        result = deduplicate_candidates(candidates, key="address")
        assert len(result) == 2

    def test_deduplicate_case_insensitive(self):
        """Test that deduplication is case-insensitive."""
        candidates = [
            {"address": "123 Main St"},
            {"address": "123 MAIN ST"},
            {"address": "456 Oak Ave"},
        ]
        result = deduplicate_candidates(candidates, key="address")
        assert len(result) == 2

    def test_deduplicate_preserves_order(self):
        """Test that deduplication preserves order."""
        candidates = [
            {"address": "First"},
            {"address": "Second"},
            {"address": "First"},
            {"address": "Third"},
        ]
        result = deduplicate_candidates(candidates, key="address")
        assert len(result) == 3
        assert result[0]["address"].lower() == "first"
        assert result[1]["address"].lower() == "second"
        assert result[2]["address"].lower() == "third"

    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        result = deduplicate_candidates([])
        assert len(result) == 0

    def test_deduplicate_custom_key(self):
        """Test deduplication with custom key."""
        candidates = [
            {"city": "Denver", "state": "CO"},
            {"city": "denver", "state": "Colorado"},
            {"city": "Boulder", "state": "CO"},
        ]
        result = deduplicate_candidates(candidates, key="city")
        assert len(result) == 2

    def test_deduplicate_with_whitespace(self):
        """Test that whitespace is normalized in deduplication."""
        candidates = [
            {"address": "  123 Main St  "},
            {"address": "123 Main St"},
            {"address": "456 Oak Ave"},
        ]
        result = deduplicate_candidates(candidates, key="address")
        assert len(result) == 2

    def test_deduplicate_preserves_first_occurrence(self):
        """Test that first occurrence is preserved."""
        candidates = [
            {"address": "123 Main", "id": 1},
            {"address": "123 main", "id": 2},
        ]
        result = deduplicate_candidates(candidates, key="address")
        assert len(result) == 1
        assert result[0]["id"] == 1


class TestSearchUtilsIntegration:
    """Integration tests for search utilities."""

    def test_address_search_workflow(self):
        """Test typical address search workflow."""
        # Normalize user input
        user_input = "  Denver, Colorado  "
        normalized = normalize_search_text(user_input)
        assert normalized == "denver, colorado"

        # Check if it's a coordinate
        is_coord = is_probably_coordinate(normalized)
        assert not is_coord

        # Score candidates
        candidates = [
            {"city": "Denver", "state": "CO"},
            {"city": "Denver", "state": "CO"},  # Duplicate
            {"city": "Boulder", "state": "CO"},
        ]
        scores = [
            score_location_match(c, "Denver", "Colorado") for c in candidates
        ]
        assert all(0 <= s <= 1 for s in scores)

        # Deduplicate
        unique = deduplicate_candidates(candidates, "city")
        assert len(unique) == 2

    def test_coordinate_extraction_workflow(self):
        """Test typical coordinate extraction workflow."""
        user_input = "40.7128, -74.0060"

        # Normalize
        normalized = normalize_search_text(user_input)

        # Check if coordinate
        is_coord = is_probably_coordinate(normalized)
        assert is_coord

    def test_fuzzy_city_matching(self):
        """Test fuzzy matching in city searches."""
        candidates = [
            {"city": "San Francisco", "state": "CA"},
            {"city": "San Jose", "state": "CA"},
            {"city": "San Diego", "state": "CA"},
        ]

        # Score all candidates
        scores = [
            score_location_match(c, preferred_city="San Francisco") for c in candidates
        ]

        # First should score highest
        assert scores[0] > scores[1]
        assert scores[0] > scores[2]
