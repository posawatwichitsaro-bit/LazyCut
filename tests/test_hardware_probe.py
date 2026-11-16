from backend.app.core.hardware_probe import (
    get_encoder_optimization_args,
    get_best_hardware_encoder,
    get_ffmpeg_binary
)

def test_encoder_optimization_args_mapping():
    assert get_encoder_optimization_args("libx264") == ["-preset", "fast", "-crf", "18"]
    nvenc_args = get_encoder_optimization_args("h264_nvenc")
    assert "-preset" in nvenc_args and "p4" in nvenc_args
    assert "-cq" in nvenc_args and "19" in nvenc_args
    assert "-b:v" in nvenc_args and "18M" in nvenc_args
    assert get_encoder_optimization_args("h264_amf") == ["-quality", "quality", "-rc", "cqp", "-qp_i", "19", "-qp_p", "21"]
    assert get_encoder_optimization_args("h264_qsv") == ["-preset", "fast", "-global_quality", "20"]
    assert get_encoder_optimization_args("custom_venc") == []

def test_hardware_probe_returns_functional_encoder():
    ffmpeg = get_ffmpeg_binary()
    assert ffmpeg is not None
    encoder = get_best_hardware_encoder()
    assert encoder in ["h264_nvenc", "h264_amf", "h264_qsv", "libx264"]
