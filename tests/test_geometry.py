import numpy as np
from defensive_recovery.geometry import compute_shape_metrics


def test_shape_metrics_expand_with_shape():
    compact = np.array([[0,0],[2,0],[4,0],[0,2],[2,2],[4,2]], dtype=float)
    spread = compact * 2
    a = compute_shape_metrics(compact)
    b = compute_shape_metrics(spread)
    assert b.width > a.width
    assert b.length > a.length
    assert b.area_proxy > a.area_proxy
    assert b.mean_nearest_neighbor > a.mean_nearest_neighbor
