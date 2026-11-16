import json
from pathlib import Path
from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(prefix="/api", tags=["Presets & Audio"])

@router.get("/presets")
def list_presets():
    from backend.app.core.preset_validator import load_and_validate_all_presets
    valid_presets, invalid = load_and_validate_all_presets(settings.presets_dir)
    return [
        {
            "id": p.get("preset_id"),
            "name": p.get("game_name", p.get("preset_id")),
            "file": f"{p.get('preset_id')}.json",
            "is_valid": True
        }
        for p in valid_presets
    ]

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
