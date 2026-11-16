# LazyCut Game Preset Authoring Guide

This guide explains how to craft, calibrate, and share new **Game Presets** for LazyCut.

---

## 📐 Anatomy of a Game Preset

Game Presets live in the `presets/` directory as declarative `.json` files. They dictate how 16:9 gameplay footage is cropped, blurred, and layered into 9:16 vertical shorts.

### Standard Schema Example

```json
{
  "preset_id": "cs2_1080p",
  "game_name": "Counter-Strike 2",
  "source_resolution": {
    "width": 1920,
    "height": 1080
  },
  "target_resolution": {
    "width": 1080,
    "height": 1920
  },
  "regions": {
    "gameplay_center": {
      "x": 420,
      "y": 0,
      "width": 1080,
      "height": 1080,
      "description": "Centered 1:1 crosshair action area"
    },
    "killfeed": {
      "x": 1450,
      "y": 30,
      "width": 450,
      "height": 220,
      "description": "Top-right elimination feed"
    }
  },
  "vertical_composition": {
    "background_blur": true,
    "background_blur_sigma": 20,
    "layers": [
      {
        "name": "blurred_background",
        "type": "background_fill",
        "scale_mode": "cover"
      },
      {
        "name": "center_gameplay",
        "type": "region_crop",
        "source_region": "gameplay_center",
        "placement": {
          "x": 0,
          "y": 420,
          "width": 1080,
          "height": 1080
        }
      },
      {
        "name": "killfeed_overlay",
        "type": "region_crop",
        "source_region": "killfeed",
        "placement": {
          "x": 315,
          "y": 120,
          "width": 450,
          "height": 220
        }
      }
    ]
  }
}
```

---

## 🔍 How to Measure Coordinates

1. Take a clean 1080p (1920x1080) in-game screenshot during a kill.
2. Open the image in Paint, Photoshop, Figma, or GIMP.
3. Select the rectangle around the killfeed / kill banner:
   - `x`: Pixels from the left edge.
   - `y`: Pixels from the top edge.
   - `width`: Selection width.
   - `height`: Selection height.
4. Save in `presets/<game_name>_1080p.json`.
5. LazyCut's built-in `PresetValidator` will automatically validate and load your preset upon restart or refresh!
