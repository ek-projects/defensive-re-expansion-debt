import numpy as np
import pytest

from defensive_recovery.dred import (
    compute_dred,
    contraction_excess,
    standardize_width,
)


def test_dred_known_series_matches_definition():
    z = np.array([-2.0, -1.5, -0.5, 1.0])
    excess = contraction_excess(z)
    np.testing.assert_allclose(excess, [1.0, 0.5, 0.0, 0.0])

    dred = compute_dred(z, fps=10.0)
    assert dred.integral == pytest.approx(0.15)
    assert dred.intensity == pytest.approx(0.375)
    assert dred.peak == pytest.approx(1.0)
    assert dred.fraction == pytest.approx(0.5)
    assert dred.n_samples == 4


def test_dred_zero_at_or_inside_threshold():
    dred = compute_dred([-1.0, -0.2, 0.0, 1.5])
    assert dred.integral == 0.0
    assert dred.intensity == 0.0
    assert dred.peak == 0.0
    assert dred.fraction == 0.0


def test_standardize_width_and_custom_threshold():
    z = standardize_width([36.0, 34.0, 30.0], median_width=34.0, robust_scale=2.0)
    np.testing.assert_allclose(z, [1.0, 0.0, -2.0])
    np.testing.assert_allclose(contraction_excess(z, threshold_z=0.5), [0.0, 0.0, 1.5])


def test_dred_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        compute_dred([])
    with pytest.raises(ValueError):
        compute_dred([0.0, np.nan])
    with pytest.raises(ValueError):
        compute_dred([0.0], fps=0)
    with pytest.raises(ValueError):
        contraction_excess([0.0], threshold_z=-1)
    with pytest.raises(ValueError):
        standardize_width([34.0], median_width=34.0, robust_scale=0)
