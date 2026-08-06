import numpy as np

from modules.optimization import (
    combine_active_coverage_masks,
    resolve_call_coverage_result,
)


def test_combines_active_responder_and_guardian_masks():
    resp_matrix = np.array([
        [True, False, False, True],
        [False, True, False, False],
        [False, False, True, False],
    ])
    guard_matrix = np.array([
        [False, True, False, False],
        [True, False, True, False],
        [False, False, False, True],
    ])

    cov_r, cov_g = combine_active_coverage_masks(
        resp_matrix,
        guard_matrix,
        active_resp_idx=[0, 2],
        active_guard_idx=[1],
    )

    np.testing.assert_array_equal(cov_r, [True, False, True, True])
    np.testing.assert_array_equal(cov_g, [True, False, True, False])


def test_no_active_units_returns_zero_masks_with_sample_width():
    resp_matrix = np.ones((2, 3), dtype=bool)
    guard_matrix = np.ones((2, 3), dtype=bool)

    cov_r, cov_g = combine_active_coverage_masks(
        resp_matrix,
        guard_matrix,
        active_resp_idx=[],
        active_guard_idx=[],
    )

    np.testing.assert_array_equal(cov_r, np.zeros(3, dtype=bool))
    np.testing.assert_array_equal(cov_g, np.zeros(3, dtype=bool))


def test_large_dataset_uses_sample_without_running_exact_builder():
    sample_result = {"total_calls": 25_000}

    def exact_builder():
        raise AssertionError("exact coverage should be skipped")

    result, fallback_reason, error = resolve_call_coverage_result(
        sample_result,
        full_call_count=304_519,
        exact_result_factory=exact_builder,
    )

    assert result is sample_result
    assert fallback_reason == "large_dataset"
    assert error is None


def test_exact_failure_returns_sample_and_error_for_logging():
    sample_result = {"total_calls": 25_000}
    expected_error = RuntimeError("projection failed")

    def exact_builder():
        raise expected_error

    result, fallback_reason, error = resolve_call_coverage_result(
        sample_result,
        full_call_count=50_000,
        exact_result_factory=exact_builder,
    )

    assert result is sample_result
    assert fallback_reason == "exact_failure"
    assert error is expected_error
