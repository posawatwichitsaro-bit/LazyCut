import json
from pathlib import Path
from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(prefix="/api", tags=["Presets & Audio"])

@router.get("/presets")
def list_presets():
    presets = []
    for f in settings.presets_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as pf:
                data = json.load(pf)
                presets.append({
                    "id": f.stem,
                    "name": data.get("game_name", f.stem),
                    "file": f.name
                })
        except Exception:
            pass
    return presets

@router.get("/vibes")
def list_vibes():
    vibes = []
    for f in settings.vibes_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as vf:
                data = json.load(vf)
                vibes.append({
                    "id": f.stem,
                    "name": data.get("name", f.stem),
                    "description": data.get("description", ""),
                    "fadeout_style": data.get("fadeout_style", "exp")
                })
        except Exception:
            pass
    return vibes

@router.get("/music")
def list_music_tracks():
    tracks = []
    extensions = {".mp3", ".wav", ".flac", ".m4a"}
    for f in settings.music_dir.iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            tracks.append({
                "filename": f.name,
                "path": str(f)
            })
    return tracks
