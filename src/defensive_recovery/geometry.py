from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ShapeMetrics:
    centroid_x: float
    centroid_y: float
    width: float
    length: float
    area_proxy: float
    mean_nearest_neighbor: float
    max_nearest_neighbor: float


def _nearest_neighbor_distances(xy: np.ndarray) -> np.ndarray:
    if len(xy) < 2:
        return np.zeros(len(xy), dtype=float)
    diff = xy[:, None, :] - xy[None, :, :]
    dist = np.sqrt(np.sum(diff * diff, axis=2))
    np.fill_diagonal(dist, np.inf)
    return np.min(dist, axis=1)


def compute_shape_metrics(xy: np.ndarray) -> ShapeMetrics:
    """Compute robust, interpretable defensive geometry from player XY positions.

    Parameters
    ----------
    xy:
        Array shaped (n_players, 2), already expressed in a consistent pitch
        coordinate system. Missing players should be removed before calling.
    """
    arr = np.asarray(xy, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2 or len(arr) < 3:
        raise ValueError("xy must contain at least three [x, y] player positions")
    if not np.isfinite(arr).all():
        raise ValueError("xy contains non-finite values")

    qx = np.quantile(arr[:, 0], [0.1, 0.9])
    qy = np.quantile(arr[:, 1], [0.1, 0.9])
    length = float(qx[1] - qx[0])
    width = float(qy[1] - qy[0])
    nn = _nearest_neighbor_distances(arr)
    centroid = arr.mean(axis=0)

    return ShapeMetrics(
        centroid_x=float(centroid[0]),
        centroid_y=float(centroid[1]),
        width=width,
        length=length,
        area_proxy=width * length,
        mean_nearest_neighbor=float(np.mean(nn)),
        max_nearest_neighbor=float(np.max(nn)),
    )
