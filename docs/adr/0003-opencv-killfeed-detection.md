# OpenCV Computer Vision for Killfeed and Action Detection

Detecting the exact timestamp and occurrence of kills in fast-paced FPS clips (such as Valorant) could be done either by querying a Vision LLM or using lightweight computer vision. We decided to use OpenCV template matching and color thresholding on predefined HUD coordinate regions (Killfeed and Kill Banner) to detect events and calculate action trim windows. This operates deterministically in milliseconds on CPU, preserves GPU resources, and avoids the token latency and cost of multi-frame Vision LLM inference.
