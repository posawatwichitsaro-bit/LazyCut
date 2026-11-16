import pytest
from backend.app.detection.killfeed_detector import ValorantKillDetector

def test_cluster_timestamps():
    detector = ValorantKillDetector()
    # Timestamps around 5.0s, 5.2s, 5.4s should merge into 1 cluster near 5.2s
    # Timestamp at 12.0s should be in its own cluster
    timestamps = [5.0, 5.2, 5.4, 12.0, 12.3]
    clusters = detector._cluster_timestamps(timestamps, cluster_window=1.0)
    assert len(clusters) == 2
    assert 5.0 <= clusters[0] <= 5.4
    assert 12.0 <= clusters[1] <= 12.3

def test_action_window_and_kill_chain_bridging():
    detector = ValorantKillDetector()
    # Two kills: at 10.0s and 12.5s (gap = 2.5s < 4.0s bridge threshold)
    # Lead-in = 3.0s, Lead-out = 1.5s
    # Kill 1 window: [7.0, 11.5]
    # Kill 2 window: [9.5, 14.0]
    # Merged window should bridge continuously from 7.0 to 14.0!
    kills = [10.0, 12.5]
    windows = detector._compute_action_windows(
        kills,
        duration=30.0,
        lead_in=3.0,
        lead_out=1.5,
        bridge_threshold=4.0
    )
    assert len(windows) == 1
    assert windows[0] == (7.0, 14.0)

def test_action_window_separated_kills():
    detector = ValorantKillDetector()
    # Two kills far apart: at 5.0s and 25.0s (gap = 20.0s > 4.0s)
    kills = [5.0, 25.0]
    windows = detector._compute_action_windows(
        kills,
        duration=35.0,
        lead_in=3.0,
        lead_out=1.5,
        bridge_threshold=4.0
    )
    assert len(windows) == 2
    assert windows[0] == (2.0, 6.5)
    assert windows[1] == (22.0, 26.5)

def test_action_window_no_kills_fallback():
    detector = ValorantKillDetector()
    # If 0 kills, fallback to entire clip
    windows = detector._compute_action_windows(
        [],
        duration=20.0,
        lead_in=3.0,
        lead_out=1.5,
        bridge_threshold=4.0
    )
    assert len(windows) == 1
    assert windows[0] == (0.0, 20.0)
