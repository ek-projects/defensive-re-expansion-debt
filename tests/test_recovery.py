import numpy as np
from defensive_recovery.recovery import detect_recovery_episodes, structural_debt


def test_structural_debt_zero_at_baseline():
    x = np.array([[10., 20.], [12., 24.]])
    baseline = np.array([10., 20.])
    scale = np.array([2., 4.])
    debt = structural_debt(x, baseline, scale)
    assert debt[0] == 0
    assert debt[1] > 0


def test_detect_break_and_recovery():
    debt = [0.4, 0.8, 2.5, 2.2, 1.6, 0.9, 0.8, 0.7, 0.6]
    episodes = detect_recovery_episodes(debt, fps=2, hold_seconds=1.0)
    assert len(episodes) == 1
    ep = episodes[0]
    assert ep.start_frame == 2
    assert ep.recovered_frame == 5
    assert ep.recovery_seconds == 1.5
    assert ep.debt_integral > 0
