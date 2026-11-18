from pathlib import Path

import numpy as np
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.detection.clip_analysis import HighlightTiming, analyze_clip, highlight_result
from backend.app.detection.highlight_curator import CombatMoment, CuratedHighlight, HighlightCurator
from backend.app.detection.killfeed_detector import KillfeedRow, match_killfeed_rows
from backend.app.engine.ai_montage_director import CandidateCut
from backend.app.engine.compositor import continuation_start, plan_cuts
from backend.app.models.entities import KillEvent, SourceClip


def test_new_row_does_not_repeat_shifted_row():
    first = np.full((16, 96), 80, dtype=np.uint8)
    second = np.full((16, 96), 160, dtype=np.uint8)
    old_row = KillfeedRow(20, first, False, 0.8)
    new_row = KillfeedRow(20, second, True, 0.9)
    shifted_row = KillfeedRow(42, first, False, 0.8)

    assert match_killfeed_rows([old_row], [new_row, shifted_row]) == {1: 0}
    assert match_killfeed_rows(
        [new_row, shifted_row], [new_row, shifted_row]
    ) == {0: 0, 1: 1}


def test_preview_and_montage_reuse_analysis_and_replace_stale_events(tmp_path, monkeypatch):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"original")
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    detector_calls = []

    def fake_curate(self, source: Path):
        detector_calls.append(source)
        moments = [
            CombatMoment(10.0, detection_score=0.8),
            CombatMoment(10.8, is_headshot=True, detection_score=0.9),
        ] if source.read_bytes() == b"original" else []
        return CuratedHighlight(source, 20.0, moments, [])

    monkeypatch.setattr(HighlightCurator, "curate_clip", fake_curate)
    with Session(engine) as session:
        clip = SourceClip(file_path=str(path), file_name=path.name, kill_count=5)
        session.add(clip)
        session.flush()
        session.add(KillEvent(clip_id=clip.id, timestamp_sec=1.0))
        session.commit()
        clip_id = clip.id

        first, revision = analyze_clip(session, clip)
        preview = highlight_result(clip, first, HighlightTiming(pre=2, post=1))
        assert preview.action_windows == [(8.0, 11.8)]
        assert clip.kill_count == 2

    with Session(engine) as session:
        clip = session.get(SourceClip, clip_id)
        cached, cached_revision = analyze_clip(session, clip)
        assert cached_revision == revision
        assert [moment.timestamp for moment in cached] == [10.0, 10.8]
        assert len(detector_calls) == 1
        assert [event.timestamp_sec for event in session.exec(select(KillEvent)).all()] == [10.0, 10.8]

        path.write_bytes(b"changed recording")
        refreshed, changed_revision = analyze_clip(session, clip)
        assert changed_revision != revision
        assert refreshed == []
        assert clip.kill_count == 0
        assert session.exec(select(KillEvent)).all() == []


def test_short_montage_budget_keeps_the_strongest_kill_and_counts_visible_events():
    candidate = CandidateCut(
        clip_id="clip", file_name="clip.mp4", raw_start=5.5, raw_end=15.0,
        kills=2, is_headshot=True, event_times=(12.5, 10.0),
    )
    cut, = plan_cuts([candidate], budget=1.0)
    assert cut.start <= 12.5 < cut.end
    assert cut.duration == 1.0
    assert cut.kills == 1

def test_continuous_source_overlap_depends_on_duration():
    assert continuation_start(120, 149) == 149
    assert continuation_start(120, 170) == 165
    assert continuation_start(120, 180) == 165
    assert continuation_start(120, 420) == 405
