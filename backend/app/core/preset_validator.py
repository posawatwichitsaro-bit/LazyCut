import json
import logging
from pathlib import Path

logger = logging.getLogger("lazycut.preset_validator")

REQUIRED_ROOT_KEYS = [
    "preset_id",
    "game_name",
    "source_resolution",
    "target_resolution",
    "regions"
]

def validate_preset_dict(data: dict) -> tuple[bool, list[str]]:
    """
    Validates a Game Preset dictionary against the LazyCut declarative schema.
    Returns (is_valid, error_messages).
    """
    errors: list[str] = []

    # 1. Check required root fields
    for k in REQUIRED_ROOT_KEYS:
        if k not in data or not data[k]:
            errors.append(f"Missing required key: '{k}'")

    # 2. Check resolution geometries
    for res_key in ["source_resolution", "target_resolution"]:
        if res_key in data and isinstance(data[res_key], dict):
            w = data[res_key].get("width")
            h = data[res_key].get("height")
            if not isinstance(w, (int, float)) or w <= 0 or not isinstance(h, (int, float)) or h <= 0:
                errors.append(f"Invalid dimensions in '{res_key}': width and height must be positive numbers.")

    # 3. Check region coordinates
    regions = data.get("regions")
    if isinstance(regions, dict):
        if not regions:
            errors.append("At least one region must be defined in 'regions'.")
        for r_name, r_coords in regions.items():
            if not isinstance(r_coords, dict):
                errors.append(f"Region '{r_name}' must be an object containing x, y, width, height.")
                continue
            x = r_coords.get("x")
            y = r_coords.get("y")
            w = r_coords.get("width")
            h = r_coords.get("height")
            if not all(isinstance(v, (int, float)) for v in [x, y, w, h]) or x < 0 or y < 0 or w <= 0 or h <= 0:
                errors.append(
                    f"Region '{r_name}' must define non-negative x, y and positive width, height."
                )
    elif "regions" in data:
        errors.append("'regions' must be a dictionary of region definitions.")

    return len(errors) == 0, errors

def load_and_validate_all_presets(
    presets_dir: Path
) -> tuple[list[dict], list[tuple[str, list[str]]]]:
    """
    Loads all JSON files from presets_dir, validating them against the schema.
    Returns (valid_presets_list, invalid_presets_list).
    """
    valid_presets: list[dict] = []
    invalid_presets: list[tuple[str, list[str]]] = []

    if not presets_dir.exists():
        return [], []

    for p_file in presets_dir.glob("*.json"):
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            is_valid, errors = validate_preset_dict(data)
            if is_valid:
                valid_presets.append(data)
            else:
                invalid_presets.append((p_file.name, errors))
                logger.warning(f"Invalid preset '{p_file.name}': {errors}")
        except Exception as e:
            invalid_presets.append((p_file.name, [f"JSON Parse Error: {e}"]))

    return valid_presets, invalid_presets
