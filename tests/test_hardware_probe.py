from backend.app.core.hardware_probe import (
    get_encoder_optimization_args,
    get_best_hardware_encoder,
    get_ffmpeg_binary
)

def test_encoder_optimization_args_mapping():
    assert get_encoder_optimization_args("libx264") == ["-preset", "fast"]
    assert get_encoder_optimization_args("h264_nvenc") == ["-preset", "p4"]
    assert get_encoder_optimization_args("h264_amf") == ["-quality", "speed"]
    assert get_encoder_optimization_args("h264_qsv") == ["-preset", "veryfast"]
    assert get_encoder_optimization_args("custom_venc") == []

def test_hardware_probe_returns_functional_encoder():
    ffmpeg = get_ffmpeg_binary()
    assert ffmpeg is not None
    encoder = get_best_hardware_encoder()
    assert encoder in ["h264_nvenc", "h264_amf", "h264_qsv", "libx264"]
