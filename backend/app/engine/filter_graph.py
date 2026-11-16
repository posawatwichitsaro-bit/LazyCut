import json
from pathlib import Path
from backend.app.core.config import settings

def build_9_16_filter_graph(
    clip_count: int,
    bgm_present: bool = False,
    ducking_db: float = -14.0,
    fadeout_style: str = "exp",
    fadeout_duration: float = 2.0,
    total_duration: float = 60.0,
    preset_path: Path | None = None
) -> tuple[str, str, str]:
    """
    Constructs an FFmpeg filter_complex script for 9:16 vertical video composition.
    Returns: (filter_script, final_video_label, final_audio_label)
    """
    if preset_path is None:
        preset_path = settings.presets_dir / "valorant_1080p.json"

    with open(preset_path, "r", encoding="utf-8") as f:
        preset = json.load(f)

    regions = preset.get("regions", {})
    center = regions.get("gameplay_center", {"x": 420, "y": 0, "width": 1080, "height": 1080})
    killfeed = regions.get("killfeed", {"x": 1480, "y": 40, "width": 420, "height": 240})

    filters: list[str] = []

    # Process each clip into 9:16 layers
    for i in range(clip_count):
        # Reset audio timestamps and lock audio rate to 48kHz with async synchronization
        filters.append(f"[{i}:a]asetpts=PTS-STARTPTS,aresample=48000:async=1[a{i}]")
        
        # Layer 1: Blurred background full bleed 1080x1920 (crisp high-clarity blur)
        filters.append(
            f"[{i}:v]setpts=PTS-STARTPTS,fps=60,scale=540:960:force_original_aspect_ratio=increase,"
            f"crop=540:960,boxblur=8:3,scale=1080:1920[bg{i}]"
        )
        # Layer 2: Center gameplay crop 1080x1080
        cx, cy, cw, ch = center["x"], center["y"], center["width"], center["height"]
        filters.append(f"[{i}:v]fps=60,crop={cw}:{ch}:{cx}:{cy}[center{i}]")

        # Layer 3: Killfeed overlay crop 420x240
        kx, ky, kw, kh = killfeed["x"], killfeed["y"], killfeed["width"], killfeed["height"]
        filters.append(f"[{i}:v]fps=60,crop={kw}:{kh}:{kx}:{ky}[kf{i}]")

        # Composite layers into 9:16 frame for clip i
        filters.append(f"[bg{i}][center{i}]overlay=0:420[comp1_{i}]")
        filters.append(f"[comp1_{i}][kf{i}]overlay=330:120,setpts=PTS-STARTPTS,fps=60[v{i}]")

    # Joint audio/video concatenation: locks video and audio together frame-by-frame
    va_inputs = "".join(f"[v{i}][a{i}]" for i in range(clip_count))
    filters.append(f"{va_inputs}concat=n={clip_count}:v=1:a=1[v_concat][game_audio]")

    final_v = "[v_concat]"
    final_a = "[game_audio]"

    # If background music is present, apply Smart Audio Ducking
    if bgm_present:
        bgm_idx = clip_count  # BGM is the last input stream
        # Map ducking dB to linear level: e.g. -14dB -> level ~ 0.20
        duck_level = max(0.05, 10 ** (ducking_db / 20.0))

        # Loop BGM to match or exceed duration
        filters.append(f"[{bgm_idx}:a]aloop=loop=-1:size=2e+09[bgm_loop]")

        # Sidechain compression: Game audio ducks BGM
        filters.append(
            f"[bgm_loop][game_audio]sidechaincompress="
            f"threshold=0.08:ratio=8:attack=20:release=300:level_in={duck_level:.2f}[ducked_bgm]"
        )

        # Mix game audio + ducked BGM
        filters.append("[game_audio][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[mixed_audio]")
        final_a = "[mixed_audio]"

    # Apply dynamic fade-out curve in the final seconds
    fade_start = max(0.0, total_duration - fadeout_duration)
    curve_type = "exp" if fadeout_style == "exp" else ("log" if fadeout_style == "log" else "tri")

    filters.append(f"{final_a}afade=t=out:st={fade_start:.2f}:d={fadeout_duration:.2f}:curve={curve_type}[a_faded]")
    final_a = "[a_faded]"

    # Also apply subtle video fade to black at the end
    filters.append(f"{final_v}fade=t=out:st={fade_start:.2f}:d={fadeout_duration:.2f}[v_faded]")
    final_v = "[v_faded]"

    filter_script = ";\n".join(filters)
    return filter_script, final_v, final_a

def build_16_9_cinema_filter_graph(
    clip_count: int,
    bgm_present: bool = False,
    ducking_db: float = -14.0,
    fadeout_style: str = "exp",
    fadeout_duration: float = 2.0,
    total_duration: float = 60.0
) -> tuple[str, str, str]:
    """
    Constructs an FFmpeg filter_complex script for 16:9 full-screen cinema montage.
    No crop: preserves full 1920x1080 field of view, stitching raw combat action cuts.
    Returns: (filter_script, final_video_label, final_audio_label)
    """
    filters: list[str] = []

    for i in range(clip_count):
        # Reset video & audio presentation timestamps, enforce 60fps and 48kHz async audio lock
        filters.append(
            f"[{i}:v]setpts=PTS-STARTPTS,fps=60,scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]"
        )
        filters.append(f"[{i}:a]asetpts=PTS-STARTPTS,aresample=48000:async=1[a{i}]")

    # Joint audio/video concatenation: locks video and audio together frame-by-frame
    va_inputs = "".join(f"[v{i}][a{i}]" for i in range(clip_count))
    filters.append(f"{va_inputs}concat=n={clip_count}:v=1:a=1[v_concat][game_audio]")

    final_v = "[v_concat]"
    final_a = "[game_audio]"

    if bgm_present:
        bgm_idx = clip_count
        duck_level = max(0.05, 10 ** (ducking_db / 20.0))
        filters.append(f"[{bgm_idx}:a]aloop=loop=-1:size=2e+09[bgm_loop]")
        filters.append(
            f"[bgm_loop][game_audio]sidechaincompress="
            f"threshold=0.08:ratio=8:attack=20:release=300:level_in={duck_level:.2f}[ducked_bgm]"
        )
        filters.append("[game_audio][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[mixed_audio]")
        final_a = "[mixed_audio]"

    fade_start = max(0.0, total_duration - fadeout_duration)
    curve_type = "exp" if fadeout_style == "exp" else ("log" if fadeout_style == "log" else "tri")

    filters.append(f"{final_a}afade=t=out:st={fade_start:.2f}:d={fadeout_duration:.2f}:curve={curve_type}[a_faded]")
    final_a = "[a_faded]"
    filters.append(f"{final_v}fade=t=out:st={fade_start:.2f}:d={fadeout_duration:.2f}[v_faded]")
    final_v = "[v_faded]"

    filter_script = ";\n".join(filters)
    return filter_script, final_v, final_a
