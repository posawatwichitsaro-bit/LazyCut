import shutil
import subprocess
from pathlib import Path
from backend.app.core.config import BASE_DIR, settings

_RESOLVED_FFMPEG: str | None = None
_RESOLVED_ENCODER: str | None = None

def get_ffmpeg_binary() -> str:
    """Resolves a valid FFmpeg binary from PATH, local bin/, or imageio-ffmpeg."""
    global _RESOLVED_FFMPEG
    if _RESOLVED_FFMPEG:
        return _RESOLVED_FFMPEG

    # 1. System PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        _RESOLVED_FFMPEG = system_ffmpeg
        return _RESOLVED_FFMPEG

    # 2. Local bin/ directory
    local_bin = BASE_DIR / "bin" / ("ffmpeg.exe" if os_is_windows() else "ffmpeg")
    if local_bin.exists():
        _RESOLVED_FFMPEG = str(local_bin)
        return _RESOLVED_FFMPEG

    # 3. imageio-ffmpeg fallback
    try:
        import imageio_ffmpeg
        imageio_path = imageio_ffmpeg.get_ffmpeg_exe()
        if imageio_path and Path(imageio_path).exists():
            _RESOLVED_FFMPEG = imageio_path
            return _RESOLVED_FFMPEG
    except Exception:
        pass

    raise RuntimeError(
        "FFmpeg executable not found! Please install FFmpeg, place ffmpeg.exe in 'bin/', "
        "or ensure 'imageio-ffmpeg' is installed."
    )

def os_is_windows() -> bool:
    import platform
    return platform.system().lower() == "windows"

def probe_encoder(encoder_name: str, ffmpeg_bin: str) -> bool:
    """Test if a given video encoder is functional on this hardware."""
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=128x128:d=0.1",
        "-c:v", encoder_name,
        "-f", "null",
        "-"
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return proc.returncode == 0
    except Exception:
        return False

def get_best_hardware_encoder() -> str:
    """Auto-probes available GPU hardware encoders with fallback to CPU libx264."""
    global _RESOLVED_ENCODER
    if _RESOLVED_ENCODER:
        return _RESOLVED_ENCODER

    if settings.preferred_encoder != "auto":
        _RESOLVED_ENCODER = settings.preferred_encoder
        return _RESOLVED_ENCODER

    ffmpeg_bin = get_ffmpeg_binary()
    candidates = [
        ("h264_nvenc", "NVIDIA NVENC"),
        ("h264_amf", "AMD AMF"),
        ("h264_qsv", "Intel QuickSync"),
        ("libx264", "Software CPU (libx264)")
    ]

    for enc, label in candidates:
        if probe_encoder(enc, ffmpeg_bin):
            _RESOLVED_ENCODER = enc
            return _RESOLVED_ENCODER

    _RESOLVED_ENCODER = "libx264"
    return _RESOLVED_ENCODER

def get_encoder_optimization_args(encoder: str) -> list[str]:
    """Returns the recommended speed/preset flags for the resolved encoder."""
    if encoder == "libx264":
        return ["-preset", "fast"]
    elif encoder == "h264_nvenc":
        return ["-preset", "p4"]
    elif encoder == "h264_amf":
        return ["-quality", "speed"]
    elif encoder == "h264_qsv":
        return ["-preset", "veryfast"]
    return []

