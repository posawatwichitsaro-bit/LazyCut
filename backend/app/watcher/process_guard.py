import psutil
from backend.app.core.config import settings

def is_game_process_running(process_name: str | None = None) -> bool:
    """Checks whether the target game executable is actively running."""
    if not settings.game_guard_enabled:
        return False

    target = (process_name or settings.target_game_process).lower()
    for proc in psutil.process_iter(["name"]):
        try:
            p_name = proc.info.get("name")
            if p_name and p_name.lower() == target:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False
