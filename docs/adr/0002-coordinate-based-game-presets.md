# Coordinate-Based JSON Presets for Vertical Video Reframing

Reframing 16:9 gameplay footage into 9:16 vertical video with stacked HUD elements can be done via real-time computer vision or predefined screen coordinate mapping. We decided to use declarative JSON coordinate presets executed via FFmpeg filter graphs instead of dynamic AI detection. This ensures deterministic output, zero GPU VRAM consumption for AI models during video rendering, and enables the open-source community to easily craft and share presets for various games and resolutions.
