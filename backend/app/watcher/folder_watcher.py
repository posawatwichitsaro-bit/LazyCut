import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from sqlmodel import Session

from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.detection.clip_analysis import analyze_clip, register_clip
from backend.app.watcher.process_guard import is_game_process_running

logger = logging.getLogger("lazycut.watcher")

class ClipFileHandler(FileSystemEventHandler):
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

        try:
            with Session(engine) as session:
                clip, _ = register_clip(session, file_path)
                if not is_game_process_running():
                    analyze_clip(session, clip)
        except Exception:
            logger.exception("Error scanning clip %s", file_path)

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

class FolderWatcherService:
    def __init__(self):
        self.observer: Observer | None = None

    def start(self, path_to_watch: str | Path):
        watch_dir = Path(path_to_watch)
        if not watch_dir.exists() or not watch_dir.is_dir():
            logger.warning(f"Watch directory does not exist: {watch_dir}")
            return

        self.stop()
        self.observer = PollingObserver() if settings.watch_polling else Observer()
        handler = ClipFileHandler()
        self.observer.schedule(handler, str(watch_dir), recursive=False)
        self.observer.start()
        logger.info(f"Started folder watcher on {watch_dir}")

        # Scan and register all existing video files in the watch directory
        self.scan_existing_clips(watch_dir)

    def scan_existing_clips(self, watch_dir: Path, analyze: bool = False) -> int:
        """Register existing clips and optionally refresh their analysis."""
        registered_count = 0
        with Session(engine) as session:
            for ext in settings.watch_extensions:
                for file_path in watch_dir.glob(f"*{ext}"):
                    if not file_path.is_file():
                        continue
                    try:
                        clip, created = register_clip(session, file_path)
                        registered_count += int(created)
                        if analyze and not is_game_process_running():
                            analyze_clip(session, clip)
                    except Exception:
                        session.rollback()
                        logger.exception("Error scanning clip %s", file_path)

        return registered_count

    def stop(self):
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            self.observer = None

watcher_service = FolderWatcherService()
