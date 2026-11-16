import os
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from sqlmodel import Session, select

from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.models.entities import SourceClip, KillEvent
from backend.app.detection.killfeed_detector import ValorantKillDetector
from backend.app.watcher.process_guard import is_game_process_running

logger = logging.getLogger("lazycut.watcher")

class ClipFileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.detector = ValorantKillDetector()

    def on_created(self, event):
        if event.is_directory:
            return
        self.process_file(Path(event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        self.process_file(Path(event.src_path))

    def process_file(self, file_path: Path):
        ext = file_path.suffix.lower()
        if ext not in settings.watch_extensions:
            return

        # Wait for file to finish writing (size stabilization check)
        if not self._wait_for_file_complete(file_path):
            return

        # Check Game Process Guard: if game is running, hold heavy scan
        if is_game_process_running():
            logger.info(f"Game process active. Staging clip without heavy scan: {file_path.name}")
            self._save_or_update_clip(file_path, scanned=False)
            return

        # Perform OpenCV Scan
        self._scan_and_save_clip(file_path)

    def _wait_for_file_complete(self, file_path: Path, timeout: float = 8.0) -> bool:
        start_time = time.time()
        last_size = -1
        while time.time() - start_time < timeout:
            if not file_path.exists():
                return False
            try:
                current_size = file_path.stat().st_size
                if current_size > 0 and current_size == last_size:
                    return True
                last_size = current_size
            except OSError:
                pass
            time.sleep(1.0)
        return False

    def _save_or_update_clip(self, file_path: Path, scanned: bool = False):
        with Session(engine) as session:
            statement = select(SourceClip).where(SourceClip.file_path == str(file_path))
            clip = session.exec(statement).first()
            if not clip:
                size = file_path.stat().st_size if file_path.exists() else 0
                clip = SourceClip(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_size=size,
                    duration=0.0,
                    kill_count=0,
                    is_verified=False
                )
                session.add(clip)
                session.commit()

    def _scan_and_save_clip(self, file_path: Path):
        try:
            from backend.app.detection.highlight_curator import HighlightCurator
            curator = HighlightCurator()
            result = curator.curate_clip(file_path)
            size = file_path.stat().st_size if file_path.exists() else 0
            kill_count = len(result.moments)
            is_verified = result.has_highlights and kill_count > 0

            with Session(engine) as session:
                statement = select(SourceClip).where(SourceClip.file_path == str(file_path))
                clip = session.exec(statement).first()
                if not clip:
                    clip = SourceClip(
                        file_path=str(file_path),
                        file_name=file_path.name,
                        file_size=size,
                        duration=result.duration,
                        kill_count=kill_count,
                        is_verified=is_verified,
                        scanned_at=time.time()
                    )
                    session.add(clip)
                else:
                    clip.duration = result.duration
                    clip.kill_count = kill_count
                    clip.is_verified = is_verified
                    clip.file_size = size

                session.commit()
                session.refresh(clip)

                # Clear old events and persist fresh kills
                for m in result.moments:
                    ke = KillEvent(
                        clip_id=clip.id,
                        timestamp_sec=m.timestamp,
                        confidence=0.95,
                        event_type="headshot" if m.is_headshot else "skull_banner"
                    )
                    session.add(ke)
                session.commit()
        except Exception as e:
            logger.error(f"Error scanning clip {file_path}: {e}")


class FolderWatcherService:
    def __init__(self):
        self.observer: Observer | None = None

    def start(self, path_to_watch: str | Path):
        watch_dir = Path(path_to_watch)
        if not watch_dir.exists() or not watch_dir.is_dir():
            logger.warning(f"Watch directory does not exist: {watch_dir}")
            return

        self.stop()
        self.observer = Observer()
        handler = ClipFileHandler()
        self.observer.schedule(handler, str(watch_dir), recursive=False)
        self.observer.start()
        logger.info(f"Started folder watcher on {watch_dir}")

        # Scan and register all existing video files in the watch directory
        self.scan_existing_clips(watch_dir)

    def scan_existing_clips(self, watch_dir: Path) -> int:
        """Discovers and registers all video files in the target directory into SQLite."""
        registered_count = 0
        import cv2
        with Session(engine) as session:
            for ext in settings.watch_extensions:
                for file_path in watch_dir.glob(f"*{ext}"):
                    stmt = select(SourceClip).where(SourceClip.file_path == str(file_path))
                    existing = session.exec(stmt).first()
                    if not existing:
                        try:
                            cap = cv2.VideoCapture(str(file_path))
                            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                            dur = frames / fps if frames > 0 else 0.0
                            cap.release()
                            size = file_path.stat().st_size
                            clip = SourceClip(
                                file_path=str(file_path),
                                file_name=file_path.name,
                                file_size=size,
                                duration=dur,
                                kill_count=0,
                                is_verified=False
                            )
                            session.add(clip)
                            registered_count += 1
                        except Exception as e:
                            logger.error(f"Error registering {file_path}: {e}")
            session.commit()
        return registered_count

    def stop(self):
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            self.observer = None

watcher_service = FolderWatcherService()
