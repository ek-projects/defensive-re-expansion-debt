from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class DREDMetrics:
    """Summary of abnormal defensive width contraction over a tracking window.

    ``integral`` is the accumulated contraction excess in z-score seconds.
    ``intensity`` is the mean contraction excess and is therefore less coupled
    to the observed window length. ``peak`` and ``fraction`` describe severity
    and persistence without introducing additional fitted parameters.
    """

    integral: float
    intensity: float
    peak: float
    fraction: float
    n_samples: int
    threshold_z: float
    fps: float


def _as_finite_1d(values: Iterable[float], *, name: str) -> np.ndarray:
    arr = np.asarray(list(values) if not isinstance(values, np.ndarray) else values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if len(arr) == 0:
        raise ValueError(f"{name} must contain at least one sample")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} contains non-finite values")
    return arr


def standardize_width(
    width: Iterable[float],
    *,
    median_width: float,
    robust_scale: float,
) -> np.ndarray:
    """Convert defensive width to the robust z-score used by DRED.

    The reference median and scale should be estimated from an appropriate
    defensive context (for the Analytics Cup implementation: match × defending
    team × out-of-possession phase).
    """

    arr = _as_finite_1d(width, name="width")
    if not np.isfinite(median_width):
        raise ValueError("median_width must be finite")
    if not np.isfinite(robust_scale) or robust_scale <= 0:
        raise ValueError("robust_scale must be finite and strictly positive")
    return (arr - float(median_width)) / float(robust_scale)


def contraction_excess(
    z_width: Iterable[float],
    *,
    threshold_z: float = 1.0,
) -> np.ndarray:
    """Return frame-level abnormal lateral contraction.

    DRED treats widths more than ``threshold_z`` robust standard deviations
    below their contextual reference as abnormal:

    ``max(-z_width - threshold_z, 0)``.
    """

    z = _as_finite_1d(z_width, name="z_width")
    if not np.isfinite(threshold_z) or threshold_z < 0:
        raise ValueError("threshold_z must be finite and non-negative")
    return np.maximum(-z - float(threshold_z), 0.0)


def compute_dred(
    z_width: Iterable[float],
    *,
    fps: float = 10.0,
    threshold_z: float = 1.0,
) -> DREDMetrics:
    """Compute DRED summaries from a contextual defensive-width z-score.

    This function is intentionally model-free. It reproduces the competition
    implementation: accumulated DRED is the sum of frame-level contraction
    excess divided by tracking frequency, while DRED intensity is its mean.
    """

    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("fps must be finite and strictly positive")
    excess = contraction_excess(z_width, threshold_z=threshold_z)
    return DREDMetrics(
        integral=float(excess.sum() / float(fps)),
        intensity=float(excess.mean()),
        peak=float(excess.max()),
        fraction=float(np.mean(excess > 0.0)),
        n_samples=int(len(excess)),
        threshold_z=float(threshold_z),
        fps=float(fps),
    )
