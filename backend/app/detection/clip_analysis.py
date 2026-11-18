import hashlib
import json
from pathlib import Path
from threading import RLock

import cv2
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlmodel import Session, select

from backend.app.core.config import settings
from backend.app.detection.highlight_curator import CombatMoment, CuratedHighlight, HighlightCurator
from backend.app.detection.killfeed_detector import CHAN_TEMPLATE_PATH, HEADSHOT_TEMPLATE_PATH
from backend.app.models.entities import ClipAnalysis, KillEvent, SourceClip, get_utc_now


class HighlightTiming(BaseModel):
    pre: float = Field(default=4.5, ge=0.0, le=60.0)
    post: float = Field(default=2.5, ge=0.5, le=60.0)


class EventSelection(BaseModel):
    revision: str
    event_indices: list[int]


# Preview, watcher and render share one process. Serialize publication so two
# simultaneous requests cannot replace the same cached result out of order.
analysis_lock = RLock()


def register_clip(session: Session, path: Path) -> tuple[SourceClip, bool]:
    path = path.resolve(strict=True)
    with analysis_lock:
        clip = session.exec(select(SourceClip).where(SourceClip.file_path == str(path))).first()
        if clip:
            return clip, False
        cap = cv2.VideoCapture(str(path))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0.0
        finally:
            cap.release()
        clip = SourceClip(
            file_path=str(path), file_name=path.name,
            file_size=path.stat().st_size, duration=duration,
        )
        session.add(clip)
        session.commit()
        session.refresh(clip)
        return clip, True


def analysis_revision(path: Path) -> str:
    stat = path.stat()
    digest = hashlib.sha256(f"rows-v1:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}".encode())
    for asset in (settings.presets_dir / "valorant_1080p.json", CHAN_TEMPLATE_PATH, HEADSHOT_TEMPLATE_PATH):
        if asset.is_file():
            digest.update(asset.read_bytes())
    return digest.hexdigest()


def analyze_clip(session: Session, clip: SourceClip) -> tuple[list[CombatMoment], str]:
    with analysis_lock:
        session.refresh(clip)
        path = Path(clip.file_path)
        revision = analysis_revision(path)
        cached = session.get(ClipAnalysis, clip.id, populate_existing=True)
        if cached and cached.revision == revision:
            return [CombatMoment(**item) for item in json.loads(cached.moments_json)], revision

        result = HighlightCurator().curate_clip(path)
        if analysis_revision(path) != revision:
            raise ValueError("Source clip changed during analysis. Try again after recording finishes.")

        payload = json.dumps([
            {
                "timestamp": moment.timestamp,
                "is_headshot": moment.is_headshot,
                "audio_energy": moment.audio_energy,
                "detection_score": moment.detection_score,
            }
            for moment in result.moments
        ])
        if cached is None:
            cached = ClipAnalysis(clip_id=clip.id, revision=revision, moments_json=payload)
        else:
            cached.revision = revision
            cached.moments_json = payload

        clip.duration = result.duration
        clip.file_size = path.stat().st_size
        clip.kill_count = len(result.moments)
        clip.is_verified = bool(result.moments)
        clip.scanned_at = get_utc_now()
        try:
            session.exec(delete(KillEvent).where(KillEvent.clip_id == clip.id))
            session.add(cached)
            session.add_all([
                KillEvent(
                    clip_id=clip.id, timestamp_sec=moment.timestamp,
                    confidence=moment.detection_score,
                    event_type="headshot" if moment.is_headshot else "skull_banner"
                )
                for moment in result.moments
            ])
            session.commit()
        except Exception:
            session.rollback()
            raise
        return result.moments, revision


def highlight_result(
    clip: SourceClip, moments: list[CombatMoment], timing: HighlightTiming
) -> CuratedHighlight:
    windows = HighlightCurator.build_action_windows(
        moments, clip.duration, lead_in=timing.pre, lead_out=timing.post,
        minimum_context=False
    )
    # Keep the event at the right edge when there is less than half a second
    # left in the source, which is the compositor's minimum cut length.
    windows = [(min(start, max(0.0, end - 0.5)), end) for start, end in windows]
    return CuratedHighlight(
        Path(clip.file_path), clip.duration, moments, windows, sum(m.score for m in moments)
    )
