import shutil
from pathlib import Path
from backend.app.core.config import settings

class DiskSafetyError(Exception):
    """Raised when available disk storage falls below safe operating margins."""
    pass

def check_disk_safety(target_dir: Path, estimated_output_bytes: int = 150 * 1024 * 1024) -> tuple[bool, int, int]:
    """
    Checks if target directory volume has enough free storage capacity.
    Returns (is_safe, free_bytes, required_bytes).
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target_dir)
    free_bytes = usage.free
    
    # Required is at least settings.min_disk_free_bytes or multiplier * estimated output
    required_bytes = max(
        settings.min_disk_free_bytes,
        int(estimated_output_bytes * settings.disk_safety_multiplier)
    )
    
    if free_bytes < required_bytes:
        free_mb = free_bytes // (1024 * 1024)
        req_mb = required_bytes // (1024 * 1024)
        raise DiskSafetyError(
            f"Insufficient disk space on {target_dir}. Available: {free_mb} MB, Required: {req_mb} MB."
        )
        
    return True, free_bytes, required_bytes
