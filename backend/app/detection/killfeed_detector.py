import json
from pathlib import Path
import cv2
import numpy as np
from backend.app.core.config import settings

class KillDetectionResult:
    def __init__(
        self,
        duration: float,
        kill_timestamps: list[float],
        action_windows: list[tuple[float, float]],
        is_verified: bool
    ):
        self.duration = duration
        self.kill_timestamps = kill_timestamps
        self.action_windows = action_windows
        self.is_verified = is_verified
        self.kill_count = len(kill_timestamps)

    def to_dict(self) -> dict:
        return {
            "duration": round(self.duration, 2),
            "kill_count": self.kill_count,
            "kill_timestamps": [round(t, 2) for t in self.kill_timestamps],
            "action_windows": [(round(s, 2), round(e, 2)) for s, e in self.action_windows],
            "is_verified": self.is_verified
        }


class ValorantKillDetector:
    def __init__(self, preset_path: Path | None = None):
        if preset_path is None:
            preset_path = settings.presets_dir / "valorant_1080p.json"

        with open(preset_path, "r", encoding="utf-8") as f:
            self.preset = json.load(f)

        regions = self.preset.get("regions", {})
        self.banner_rect = regions.get("skull_banner", {"x": 840, "y": 780, "width": 240, "height": 160})
        self.detection_cfg = self.preset.get("detection_config", {})

        # Color thresholds in HSV
        self.red_lower = np.array(self.detection_cfg.get("banner_red_lower", [0, 130, 130]), dtype=np.uint8)
        self.red_upper = np.array(self.detection_cfg.get("banner_red_upper", [10, 255, 255]), dtype=np.uint8)
        self.yellow_lower = np.array(self.detection_cfg.get("banner_yellow_lower", [15, 150, 150]), dtype=np.uint8)
        self.yellow_upper = np.array(self.detection_cfg.get("banner_yellow_upper", [35, 255, 255]), dtype=np.uint8)
        self.min_density = self.detection_cfg.get("min_kill_pixel_density", 0.08)

    def analyze_clip(
        self,
        video_path: str | Path,
        lead_in: float = 3.0,
        lead_out: float = 1.5,
        bridge_threshold: float = 4.0,
        sample_fps: float = 4.0
    ) -> KillDetectionResult:
        """
        Scans a Source Clip for elimination banners and calculates the Action Windows.
        """
        video_path_str = str(video_path)
        cap = cv2.VideoCapture(video_path_str)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path_str}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if total_frames > 0 else 0.0

        if duration < 1.0:
            cap.release()
            return KillDetectionResult(duration, [], [(0.0, duration)], False)

        frame_step = max(1, int(round(fps / sample_fps)))
        raw_kill_timestamps: list[float] = []

        bx = self.banner_rect["x"]
        by = self.banner_rect["y"]
        bw = self.banner_rect["width"]
        bh = self.banner_rect["height"]
        banner_area = bw * bh

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                h, w = frame.shape[:2]
                
                # Scale coordinates if video resolution differs from 1920x1080
                sx = w / 1920.0
                sy = h / 1080.0
                cx = int(bx * sx)
                cy = int(by * sy)
                cw = int(bw * sx)
                ch = int(bh * sy)

                # Ensure crop stays within image bounds
                crop = frame[max(0, cy):min(h, cy + ch), max(0, cx):min(w, cx + cw)]
                if crop.size > 0:
                    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    mask_red1 = cv2.inRange(hsv, self.red_lower, self.red_upper)
                    mask_red2 = cv2.inRange(hsv, np.array([170, 130, 130], dtype=np.uint8), np.array([180, 255, 255], dtype=np.uint8))
                    mask_yellow = cv2.inRange(hsv, self.yellow_lower, self.yellow_upper)
                    combined_mask = cv2.bitwise_or(cv2.bitwise_or(mask_red1, mask_red2), mask_yellow)

                    active_pixels = cv2.countNonZero(combined_mask)
                    density = active_pixels / (crop.shape[0] * crop.shape[1])

                    if density >= self.min_density:
                        current_sec = frame_idx / fps
                        raw_kill_timestamps.append(current_sec)

            frame_idx += 1

        cap.release()

        # Cluster kill timestamps: merge hits within 1.0 second into a single kill event
        clustered_kills = self._cluster_timestamps(raw_kill_timestamps, cluster_window=1.0)

        # Build Action Windows with Lead-in, Lead-out, and Kill-Chain Bridging
        action_windows = self._compute_action_windows(
            clustered_kills,
            duration=duration,
            lead_in=lead_in,
            lead_out=lead_out,
            bridge_threshold=bridge_threshold
        )

        is_verified = len(clustered_kills) > 0
        return KillDetectionResult(
            duration=duration,
            kill_timestamps=clustered_kills,
            action_windows=action_windows,
            is_verified=is_verified
        )

    def _cluster_timestamps(self, timestamps: list[float], cluster_window: float = 1.0) -> list[float]:
        if not timestamps:
            return []

        clusters: list[list[float]] = []
        for t in sorted(timestamps):
            if not clusters or t - clusters[-1][-1] > cluster_window:
                clusters.append([t])
            else:
                clusters[-1].append(t)

        # Return the peak / center timestamp of each cluster
        return [sum(c) / len(c) for c in clusters]

    def _compute_action_windows(
        self,
        kills: list[float],
        duration: float,
        lead_in: float,
        lead_out: float,
        bridge_threshold: float
    ) -> list[tuple[float, float]]:
        if not kills:
            # If no kill verified, fall back to entire clip
            return [(0.0, duration)]

        # Initial windows around each kill
        raw_windows: list[tuple[float, float]] = []
        for k in kills:
            start = max(0.0, k - lead_in)
            end = min(duration, k + lead_out)
            raw_windows.append((start, end))

        # Merge overlapping or near windows (Kill-Chain Bridging)
        merged: list[tuple[float, float]] = []
        for start, end in sorted(raw_windows, key=lambda w: w[0]):
            if not merged:
                merged.append((start, end))
            else:
                prev_start, prev_end = merged[-1]
                # If gap is smaller than bridge threshold, bridge them
                if start - prev_end <= bridge_threshold:
                    merged[-1] = (prev_start, max(prev_end, end))
                else:
                    merged.append((start, end))

        return merged
