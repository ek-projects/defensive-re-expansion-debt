from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import numpy as np


@dataclass(frozen=True)
class RecoveryEpisode:
    start_frame: int
    recovered_frame: int | None
    recovery_seconds: float | None
    debt_integral: float
    peak_debt: float


def structural_debt(features: np.ndarray, baseline: np.ndarray, scale: np.ndarray) -> np.ndarray:
    """Return frame-level structural debt as robust standardized distance.

    A score near zero means the defensive shape resembles its context baseline;
    larger values indicate greater structural displacement. ``scale`` is a
    robust feature scale such as MAD/IQR and must be positive.
    """
    x = np.asarray(features, dtype=float)
    b = np.asarray(baseline, dtype=float)
    s = np.asarray(scale, dtype=float)
    if x.ndim != 2:
        raise ValueError("features must be 2D")
    if b.shape != (x.shape[1],) or s.shape != (x.shape[1],):
        raise ValueError("baseline and scale must match feature columns")
    if np.any(s <= 0):
        raise ValueError("scale must be strictly positive")
    z = (x - b) / s
    return np.sqrt(np.mean(z * z, axis=1))


def detect_recovery_episodes(
    debt: Iterable[float],
    *,
    fps: float,
    break_threshold: float = 2.0,
    recovery_threshold: float = 1.0,
    hold_seconds: float = 1.0,
) -> list[RecoveryEpisode]:
    """Detect break→recovery episodes from a frame-level structural-debt series.

    A break begins when debt crosses ``break_threshold``. Recovery is declared
    only after debt remains at or below ``recovery_threshold`` for
    ``hold_seconds``. The integral captures both severity and duration.
    """
    d = np.asarray(list(debt), dtype=float)
    if fps <= 0:
        raise ValueError("fps must be positive")
    if len(d) == 0:
        return []
    if not np.isfinite(d).all():
        raise ValueError("debt contains non-finite values")

    hold = max(1, int(round(hold_seconds * fps)))
    episodes: list[RecoveryEpisode] = []
    i = 0
    n = len(d)

    while i < n:
        if d[i] < break_threshold:
            i += 1
            continue
        start = i
        recovered = None
        j = i + 1
        while j < n:
            if d[j] <= recovery_threshold:
                end_hold = min(n, j + hold)
                if end_hold - j == hold and np.all(d[j:end_hold] <= recovery_threshold):
                    recovered = j
                    break
            j += 1

        end = recovered if recovered is not None else n - 1
        segment = d[start : end + 1]
        excess = np.maximum(segment - recovery_threshold, 0.0)
        integral = float(np.sum(excess) / fps)
        recovery_seconds = None if recovered is None else float((recovered - start) / fps)
        episodes.append(
            RecoveryEpisode(
                start_frame=start,
                recovered_frame=recovered,
                recovery_seconds=recovery_seconds,
                debt_integral=integral,
                peak_debt=float(np.max(segment)),
            )
        )
        i = (recovered + hold) if recovered is not None else n
    return episodes
