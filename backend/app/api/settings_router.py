from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.core.hardware_probe import get_best_hardware_encoder, get_ffmpeg_binary
from backend.app.watcher.folder_watcher import watcher_service
from backend.app.watcher.process_guard import is_game_process_running

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class SettingsUpdate(BaseModel):
    watch_path: str | None = None
    game_guard_enabled: bool | None = None
    preferred_encoder: str | None = None

@router.get("")
def get_settings():
    return {
        "watch_path": settings.watch_path,
        "game_guard_enabled": settings.game_guard_enabled,
        "is_game_running": is_game_process_running(),
        "preferred_encoder": settings.preferred_encoder,
        "resolved_encoder": get_best_hardware_encoder(),
        "ffmpeg_bin": get_ffmpeg_binary()
    }

@router.post("")
def update_settings(payload: SettingsUpdate):
    if payload.watch_path is not None:
        settings.watch_path = payload.watch_path
        if payload.watch_path and Path(payload.watch_path).exists():
            watcher_service.start(payload.watch_path)
        else:
            watcher_service.stop()

    if payload.game_guard_enabled is not None:
        settings.game_guard_enabled = payload.game_guard_enabled

    if payload.preferred_encoder is not None:
        settings.preferred_encoder = payload.preferred_encoder

    return get_settings()

@router.get("/hardware")
def probe_hardware():
    return {
        "ffmpeg_binary": get_ffmpeg_binary(),
        "detected_encoder": get_best_hardware_encoder(),
        "configured_encoder": settings.preferred_encoder
    }
