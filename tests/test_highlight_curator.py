import os
from pathlib import Path
import pytest
import numpy as np
from backend.app.detection.highlight_curator import (
    HighlightCurator,
    CombatMoment,
    CuratedHighlight
)

def test_score_highlight_moment():
    curator = HighlightCurator()
    
    # Double Headshot moment (Top tier)
    ace_moment = CombatMoment(
        timestamp=42.0,
        kill_count=2,
        is_headshot=True,
        audio_energy=7500.0,
        is_player_kill=True
    )
    score_ace = curator.score_moment(ace_moment)

    # Single body kill
    single_moment = CombatMoment(
        timestamp=10.0,
        kill_count=1,
        is_headshot=False,
        audio_energy=3000.0,
        is_player_kill=True
    )
    score_single = curator.score_moment(single_moment)

    # Spawn walking (No kills, quiet)
    idle_moment = CombatMoment(
        timestamp=5.0,
        kill_count=0,
        is_headshot=False,
        audio_energy=500.0,
        is_player_kill=False
    )
    score_idle = curator.score_moment(idle_moment)

    assert score_ace > score_single
    assert score_single > score_idle
    assert score_idle == 0
    assert curator.is_worth_keeping(ace_moment) is True
    assert curator.is_worth_keeping(idle_moment) is False

def test_action_window_bridging_multi_kills():
    curator = HighlightCurator()
    moments = [
        CombatMoment(timestamp=10.0, kill_count=1, is_headshot=True, audio_energy=6000.0, is_player_kill=True),
        CombatMoment(timestamp=12.5, kill_count=1, is_headshot=True, audio_energy=7000.0, is_player_kill=True),
    ]
    # Kills are 2.5s apart (< 4.0s bridge threshold), should bridge into a single action window
    windows = curator.build_action_windows(moments, total_duration=30.0, lead_in=2.0, lead_out=1.2)
    assert len(windows) == 1
    start, end = windows[0]
    # Start = 10.0 - 2.0 = 8.0, End = 12.5 + 1.2 = 13.7
    assert 7.8 <= start <= 8.2
    assert 13.5 <= end <= 13.9

def test_curate_real_user_valorant_clip():
    real_clip = Path(r"D:\Clips\Valorant\Project 05_10-09-2026_19-23-11-560.mp4")
    if not real_clip.exists():
        pytest.skip("Real clip not present on disk")

    curator = HighlightCurator()
    result = curator.curate_clip(real_clip)

    assert result.has_highlights is True
    assert len(result.action_windows) >= 1
    # The double headshot is around 38.5s - 45.0s
    highlight_start, highlight_end = result.action_windows[0]
    assert 34.0 <= highlight_start <= 41.0
    assert 42.0 <= highlight_end <= 48.0
    # Must completely discard spawn walking (0 to 30s)
    assert highlight_start > 30.0
