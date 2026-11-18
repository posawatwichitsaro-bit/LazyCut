import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR
PRESETS_DIR = BASE_DIR / "presets"
VIBES_DIR = BASE_DIR / "vibes"
MUSIC_DIR = BASE_DIR / "music"
EXPORTS_DIR = BASE_DIR / "exports"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    app_name: str = "LazyCut"
    app_version: str = "0.1.0-mvp"
    
    # Storage & DB
    database_url: str = f"sqlite:///{BASE_DIR / 'lazycut.db'}"
    exports_dir: Path = EXPORTS_DIR
    music_dir: Path = MUSIC_DIR
    presets_dir: Path = PRESETS_DIR
    vibes_dir: Path = VIBES_DIR
    
    # Watcher & Ingestion
    watch_path: str = ""
    watch_polling: bool = False
    watch_extensions: list[str] = [".mp4", ".mkv", ".mov", ".avi"]
    game_guard_enabled: bool = True
    target_game_process: str = "VALORANT.exe"
    
    # Video & Encoder
    preferred_encoder: str = "auto"  # 'auto', 'h264_nvenc', 'h264_amf', 'h264_qsv', 'libx264'
    default_fps: int = 60
    default_vibe: str = "hype_montage"
    default_preset: str = "valorant_1080p"
    max_montage_duration_seconds: int = 900  # 15 minutes hard cap
    min_clip_duration_seconds: float = 5.0
    max_clip_duration_seconds: float = 45.0
    
    # Notifications & Webhooks
    discord_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # Disk Safety Guard
    min_disk_free_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB minimum free
    disk_safety_multiplier: float = 3.0

settings = Settings()
