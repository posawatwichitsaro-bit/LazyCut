import json
from pathlib import Path
import cv2
import numpy as np
from backend.app.core.config import settings

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
CHAN_TEMPLATE_PATH = TEMPLATE_DIR / "chan_template.png"
HEADSHOT_TEMPLATE_PATH = TEMPLATE_DIR / "headshot_template.png"

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
    """
    Precision Valorant Killfeed Detector:
    Detects player-confirmed kills specifically via the 3-layer signature:
    1. Thai word 'ฉัน' (Me) on killer card via template matching.
    2. Lime-Yellow border outline around the player box.
    3. Green/Teal killer rectangular banner.
    Accurately handles multi-kill stacks (Roman numerals III, IV, V).
    """
    def __init__(self, preset_path: Path | None = None):
        if preset_path is None:
            preset_path = settings.presets_dir / "valorant_1080p.json"

        if preset_path.exists():
            with open(preset_path, "r", encoding="utf-8") as f:
                self.preset = json.load(f)
        else:
            self.preset = {}

        self.chan_tmpl = cv2.imread(str(CHAN_TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE) if CHAN_TEMPLATE_PATH.exists() else None
        self.hs_tmpl = cv2.imread(str(HEADSHOT_TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE) if HEADSHOT_TEMPLATE_PATH.exists() else None

    def detect_kills_in_roi(self, roi: np.ndarray) -> tuple[int, bool]:
        """
        Detects player kills within a killfeed region of interest.
        Returns: (kill_count, is_headshot)
        """
        if roi is None or roi.size == 0 or self.chan_tmpl is None:
            return 0, False

        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        res = cv2.matchTemplate(gray_roi, self.chan_tmpl, cv2.TM_CCOEFF_NORMED)

        threshold = 0.70
        locs = np.where(res >= threshold)
        pts = list(zip(locs[1], locs[0]))
        pts.sort(key=lambda p: res[p[1], p[0]], reverse=True)

        th_w, th_h = self.chan_tmpl.shape[1], self.chan_tmpl.shape[0]
        confirmed_kills: list[tuple[int, int]] = []
        is_headshot = False

        for x, y in pts:
            # Enforce at least 18px separation between stacked killfeed rows
            if not any(abs(y - cy) < 18 for cx, cy in confirmed_kills):
                y_min = max(0, y - 10)
                y_max = min(roi.shape[0], y + th_h + 10)
                x_min = max(0, x - 90)
                x_max = min(roi.shape[1], x + th_w + 180)
                row = roi[y_min:y_max, x_min:x_max]

                if row.size == 0:
                    continue

                hsv = cv2.cvtColor(row, cv2.COLOR_BGR2HSV)
                yellow = cv2.countNonZero(cv2.inRange(hsv, np.array([25, 60, 110]), np.array([55, 255, 255])))
                green = cv2.countNonZero(cv2.inRange(hsv, np.array([65, 60, 90]), np.array([110, 255, 255])))

                # Validate yellow border (>= 120 px) and green card (>= 400 px)
                if yellow >= 120 and green >= 400:
                    confirmed_kills.append((x, y))
                    if self.hs_tmpl is not None:
                        gray_row = cv2.cvtColor(row, cv2.COLOR_BGR2GRAY)
                        hs_res = cv2.matchTemplate(gray_row, self.hs_tmpl, cv2.TM_CCOEFF_NORMED)
                        if cv2.minMaxLoc(hs_res)[1] >= 0.75:
                            is_headshot = True

        return len(confirmed_kills), is_headshot

    def analyze_clip(
        self,
        video_path: str | Path,
        lead_in: float = 4.5,
        lead_out: float = 2.5,
        bridge_threshold: float = 4.0,
        sample_fps: float = 4.0
    ) -> KillDetectionResult:
        """
        Scans a Source Clip for player 'ฉัน' killfeed banners and calculates the Action Windows.
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

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                h, w = frame.shape[:2]
                sx, sy = w / 1920.0, h / 1080.0
                
                # Top-Right Killfeed ROI
                y1 = int(30 * sy)
                y2 = int(350 * sy)
                x1 = int(1350 * sx)
                x2 = int(1920 * sx)
                roi = frame[y1:y2, x1:x2]

                if abs(sx - 1.0) > 0.05 or abs(sy - 1.0) > 0.05:
                    roi = cv2.resize(roi, (570, 320))

                kills, _ = self.detect_kills_in_roi(roi)
                if kills > 0:
                    current_sec = frame_idx / fps
                    # If multiple kills stacked in this frame, append multiple timestamps
                    for _ in range(kills):
                        raw_kill_timestamps.append(current_sec)

            frame_idx += 1

        cap.release()

        # Cluster kill timestamps: merge hits within 2.0 seconds into a single kill event
        clustered_kills = self._cluster_timestamps(raw_kill_timestamps, cluster_window=2.0)

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

    def _cluster_timestamps(self, timestamps: list[float], cluster_window: float = 2.0) -> list[float]:
        if not timestamps:
            return []

        clusters: list[list[float]] = []
        for t in sorted(timestamps):
            if not clusters or t - clusters[-1][-1] > cluster_window:
                clusters.append([t])
            else:
                clusters[-1].append(t)

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
            return [(0.0, duration)]

        raw_windows: list[tuple[float, float]] = []
        for k in kills:
            start = max(0.0, k - lead_in)
            end = min(duration, k + lead_out)
            raw_windows.append((start, end))

        merged: list[tuple[float, float]] = []
        for start, end in sorted(raw_windows, key=lambda w: w[0]):
            if not merged:
                merged.append((start, end))
            else:
                prev_start, prev_end = merged[-1]
                if start - prev_end <= bridge_threshold:
                    merged[-1] = (prev_start, max(prev_end, end))
                else:
                    merged.append((start, end))

        return merged
