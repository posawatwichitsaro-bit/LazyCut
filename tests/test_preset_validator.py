import pytest
from backend.app.core.config import settings
from backend.app.core.preset_validator import validate_preset_dict, load_and_validate_all_presets

def test_validate_valid_preset():
    valid = {
        "preset_id": "test_game_1080p",
        "game_name": "Test Game",
        "source_resolution": {"width": 1920, "height": 1080},
        "target_resolution": {"width": 1080, "height": 1920},
        "regions": {
            "gameplay_center": {"x": 420, "y": 0, "width": 1080, "height": 1080},
            "killfeed": {"x": 1400, "y": 50, "width": 400, "height": 200}
        },
        "vertical_composition": {"layers": []}
    }
    is_valid, errors = validate_preset_dict(valid)
    assert is_valid is True
    assert len(errors) == 0

def test_validate_missing_required_keys():
    broken = {
        "preset_id": "broken_game"
        # missing game_name, source_resolution, target_resolution, regions
    }
    is_valid, errors = validate_preset_dict(broken)
    assert is_valid is False
    error_str = " ".join(errors)
    assert "game_name" in error_str
    assert "regions" in error_str

def test_validate_invalid_region_coordinates():
    invalid_coords = {
        "preset_id": "bad_coords",
        "game_name": "Bad Coords",
        "source_resolution": {"width": 1920, "height": 1080},
        "target_resolution": {"width": 1080, "height": 1920},
        "regions": {
            "killfeed": {"x": -10, "y": 0, "width": 0, "height": 100}  # Negative x or zero width
        }
    }
    is_valid, errors = validate_preset_dict(invalid_coords)
    assert is_valid is False
    assert any("killfeed" in e for e in errors)

def test_load_all_built_in_presets():
    # Should validate all built-in JSON presets in presets/ (including valorant_1080p.json)
    valid_presets, invalid_presets = load_and_validate_all_presets(settings.presets_dir)
    assert len(valid_presets) >= 1
    assert any(p["preset_id"] == "valorant_1080p" for p in valid_presets)
    assert len(invalid_presets) == 0
