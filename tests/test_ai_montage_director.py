import re
from pathlib import Path
from datetime import datetime
import pytest

from backend.app.engine.ai_montage_director import (
    AIMontageDirector,
    CandidateCut,
    OptimizedCut,
    parse_clip_chronological_key
)

def test_parse_clip_chronological_key():
    # Outplayed Valorant format: Valorant_MM-DD-YYYY_HH-MM-SS-X.mp4
    f1 = "Valorant_11-22-2024_15-40-51-0.mp4"
    f2 = "Valorant_11-22-2024_16-0-0-0.mp4"
    f3 = "Valorant_11-22-2024_17-9-2-0.mp4"

    k1 = parse_clip_chronological_key(f1)
    k2 = parse_clip_chronological_key(f2)
    k3 = parse_clip_chronological_key(f3)

    assert k1 < k2 < k3

def test_chronological_sorting():
    director = AIMontageDirector()
    cuts = [
        CandidateCut(clip_id="c3", file_name="Valorant_11-22-2024_17-9-2-0.mp4", raw_start=10.0, raw_end=15.0, kills=3, is_headshot=True, energy=8000),
        CandidateCut(clip_id="c1", file_name="Valorant_11-22-2024_15-40-51-0.mp4", raw_start=5.0, raw_end=9.0, kills=1, is_headshot=False, energy=5000),
        CandidateCut(clip_id="c2", file_name="Valorant_11-22-2024_16-0-0-0.mp4", raw_start=20.0, raw_end=25.0, kills=2, is_headshot=True, energy=7000),
    ]

    sorted_cuts = director.sort_chronologically(cuts)
    assert [c.clip_id for c in sorted_cuts] == ["c1", "c2", "c3"]

def test_ai_secondary_optimization():
    director = AIMontageDirector()
    cuts = [
        CandidateCut(clip_id="c1", file_name="Valorant_11-22-2024_15-40-51-0.mp4", raw_start=5.0, raw_end=11.0, kills=1, is_headshot=False, energy=5000),
        CandidateCut(clip_id="c2", file_name="Valorant_11-22-2024_16-0-0-0.mp4", raw_start=20.0, raw_end=27.0, kills=2, is_headshot=True, energy=7500),
    ]

    optimized = director.optimize_edl(cuts, target_budget=10.0)
    assert len(optimized) == 2
    # Verify chronological sequence is maintained
    assert optimized[0].clip_id == "c1"
    assert optimized[1].clip_id == "c2"

    total_dur = sum(c.duration for c in optimized)
    assert total_dur <= 10.5
    # The climax clip (c2 with double kill) should receive high pacing priority
    assert optimized[1].duration >= optimized[0].duration
