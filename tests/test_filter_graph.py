import pytest
from backend.app.engine.filter_graph import build_9_16_filter_graph

def test_build_9_16_filter_graph_without_bgm():
    filter_script, v_out, a_out = build_9_16_filter_graph(
        clip_count=2,
        bgm_present=False,
        total_duration=30.0
    )
    # Check that scale, crop, boxblur, joint concat, and fade are present
    assert "boxblur=" in filter_script
    assert "scale=1080:1920" in filter_script
    assert "concat=n=2:v=1:a=1" in filter_script
    assert "aresample=48000:async=1" in filter_script
    assert "afade=t=out" in filter_script
    assert "fade=t=out" in filter_script
    assert v_out == "[v_faded]"
    assert a_out == "[a_faded]"

def test_build_9_16_filter_graph_with_bgm_ducking():
    filter_script, v_out, a_out = build_9_16_filter_graph(
        clip_count=3,
        bgm_present=True,
        ducking_db=-14.0,
        fadeout_style="exp",
        total_duration=45.0
    )
    # Check that sidechaincompress is inserted with proper level and aloop
    assert "aloop=loop=-1" in filter_script
    assert "sidechaincompress=" in filter_script
    assert "level_in=0.20" in filter_script
    assert "amix=inputs=2" in filter_script
    assert "curve=exp" in filter_script
