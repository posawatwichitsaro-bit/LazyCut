import json
import subprocess
from pathlib import Path
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.core.hardware_probe import get_ffmpeg_binary

class CombatMoment:
    def __init__(
        self,
        timestamp: float,
        kill_count: int = 1,
        is_headshot: bool = False,
        audio_energy: float = 0.0,
        is_player_kill: bool = True
    ):
        self.timestamp = timestamp
        self.kill_count = kill_count
        self.is_headshot = is_headshot
        self.audio_energy = audio_energy
        self.is_player_kill = is_player_kill
        self.score = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": round(self.timestamp, 2),
            "kill_count": self.kill_count,
            "is_headshot": self.is_headshot,
            "audio_energy": round(self.audio_energy, 1),
            "score": round(self.score, 1)
        }

class CuratedHighlight:
    def __init__(
        self,
        file_path: Path,
        duration: float,
        moments: list[CombatMoment],
        action_windows: list[tuple[float, float]],
        total_score: float = 0.0
    ):
        self.file_path = file_path
        self.duration = duration
        self.moments = moments
        self.action_windows = action_windows
        self.total_score = total_score
        self.has_highlights = len(action_windows) > 0 and total_score > 0

    def to_dict(self) -> dict:
        return {
            "file_name": self.file_path.name,
            "duration": round(self.duration, 2),
            "has_highlights": self.has_highlights,
            "total_score": round(self.total_score, 1),
            "action_windows": [(round(s, 2), round(e, 2)) for s, e in self.action_windows],
            "moments": [m.to_dict() for m in self.moments]
        }

class HighlightCurator:
    """
    AI Combat Highlight Curator:
    Analyzes audio energy peaks (gunfire/kill chimes) and visual combat cues (killfeed & banner)
    to curate ONLY beautiful shots (Headshots, Multi-kills, Clutch flicks) and discard non-combat walking.
    """
    def __init__(self, preset_path: Path | None = None):
        self.ffmpeg_bin = get_ffmpeg_binary()

    def score_moment(self, moment: CombatMoment) -> float:
        """Scores a moment: Headshots and Multi-kills receive top hype scores."""
        if not moment.is_player_kill or moment.kill_count == 0:
            moment.score = 0.0
            return 0.0

        score = 50.0 * moment.kill_count
        if moment.is_headshot:
            score += 50.0
        if moment.kill_count >= 2:
            score += 100.0  # Multi-kill bonus
        if moment.audio_energy > 5000.0:
            score += 50.0  # High audio excitement
        
        moment.score = score
        return score

    def is_worth_keeping(self, moment: CombatMoment) -> bool:
        return self.score_moment(moment) >= 50.0

    def build_action_windows(
        self,
        moments: list[CombatMoment],
        total_duration: float,
        lead_in: float = 4.5,
        lead_out: float = 2.5,
        bridge_threshold: float = 3.5
    ) -> list[tuple[float, float]]:
        """
        Calculates precision action windows around confirmed combat moments.
        Bridges moments occurring within bridge_threshold (3.5s).
        Ensures each window has ample context (minimum 6.0s duration).
        """
        valid_moments = [m for m in moments if self.is_worth_keeping(m)]
        if not valid_moments:
            return []

        sorted_timestamps = sorted([m.timestamp for m in valid_moments])
        
        # Cluster timestamps that occur close to each other
        clusters: list[list[float]] = []
        for t in sorted_timestamps:
            if not clusters:
                clusters.append([t])
            else:
                if t - clusters[-1][-1] <= bridge_threshold:
                    clusters[-1].append(t)
                else:
                    clusters.append([t])

        windows: list[tuple[float, float]] = []
        for cluster in clusters:
            start = max(0.0, cluster[0] - lead_in)
            end = min(total_duration, cluster[-1] + lead_out)
            
            # If standard lead-in (>=4.0) and window is under 6.0s, expand to guarantee readable context
            if lead_in >= 4.0 and end - start < 6.0 and total_duration >= 6.0:
                mid = (start + end) / 2.0
                start = max(0.0, mid - 3.5)
                end = min(total_duration, start + 7.0)
                if end >= total_duration:
                    start = max(0.0, total_duration - 7.0)
            
            windows.append((start, end))

        # Merge overlapping or closely adjacent windows to ensure fluid, non-fragmented scenes
        merged_windows: list[tuple[float, float]] = []
        for w in sorted(windows, key=lambda item: item[0]):
            if not merged_windows:
                merged_windows.append(w)
            else:
                prev_start, prev_end = merged_windows[-1]
                if w[0] <= prev_end + 1.0:
                    merged_windows[-1] = (prev_start, max(prev_end, w[1]))
                else:
                    merged_windows.append(w)
        windows = merged_windows

        # Score each action window based on the combat moments it contains
        scored_windows: list[tuple[tuple[float, float], float]] = []
        for w_start, w_end in windows:
            moments_in_window = [m for m in valid_moments if w_start <= m.timestamp <= w_end]
            w_score = sum(m.score for m in moments_in_window)
            if len(moments_in_window) >= 2:
                w_score += 150.0  # Multi-kill sequence bonus
            scored_windows.append(((w_start, w_end), w_score))

        # Sort action windows by score descending (highest quality/hype first)
        scored_windows.sort(key=lambda item: item[1], reverse=True)
        return [sw[0] for sw in scored_windows]

    def extract_audio_peaks(self, video_path: Path, sample_rate: int = 16000) -> list[tuple[float, float]]:
        """Extracts audio RMS energy over 0.5s windows to detect intense combat."""
        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-"
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
            if proc.returncode != 0 or not proc.stdout:
                return []
            audio = np.frombuffer(proc.stdout, dtype=np.int16)
        except Exception:
            return []

        if len(audio) == 0:
            return []

        window_size = int(sample_rate * 0.5)
        peaks: list[tuple[float, float]] = []
        for i in range(0, len(audio), window_size):
            chunk = audio[i:i + window_size].astype(np.float32)
            rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
            t = i / sample_rate
            peaks.append((t, rms))

        return peaks

    def curate_clip(
        self,
        video_path: Path,
        lead_in: float = 4.5,
        lead_out: float = 2.5
    ) -> CuratedHighlight:
        """
        Scans a video file using high-precision Kill Banner visual detection (Red Skull & Gold Finisher)
        combined with audio combat energy to curate genuine kills with clear match context.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open clip: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if total_frames > 0 else 0.0

        if duration < 0.5:
            cap.release()
            return CuratedHighlight(video_path, duration, [], [], 0.0)

        # 1. Extract audio peaks for energy profiling
        audio_peaks = self.extract_audio_peaks(video_path)
        energy_map = {round(t * 2) / 2.0: e for t, e in audio_peaks}

        # 2. Sample frames at ~3 fps (step = max(1, fps * 0.33))
        # Kill banners persist on screen for ~1.5 seconds, guaranteeing 100% catch rate
        step = max(1, int(fps * 0.33))
        combat_moments: list[CombatMoment] = []
        last_kill_t = -10.0

        frame_idx = 0
        while cap.isOpened() and frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            t = frame_idx / fps

            h, w = frame.shape[:2]
            scale = (w * h) / (1920.0 * 1080.0)

            # Center-bottom Kill Banner ROI: x: 42%..58%, y: 76%..93%
            y1, y2 = int(0.76 * h), int(0.93 * h)
            x1, x2 = int(0.42 * w), int(0.58 * w)
            cb = frame[y1:y2, x1:x2]
            hsv_cb = cv2.cvtColor(cb, cv2.COLOR_BGR2HSV)

            # Red Skull Banner (Default & standard skin finishers)
            red1 = cv2.inRange(hsv_cb, (0, 140, 120), (10, 255, 255))
            red2 = cv2.inRange(hsv_cb, (170, 140, 120), (180, 255, 255))
            red_count = cv2.countNonZero(red1 | red2)

            # Gold / Yellow Finisher Banner (Champions, Kuronami, Prime, Sovereign)
            gold = cv2.inRange(hsv_cb, (15, 120, 140), (32, 255, 255))
            gold_count = cv2.countNonZero(gold)

            # Check Killfeed headshot icon (top right: x 72%..100%, y 3%..28%)
            kf_roi = frame[int(0.03 * h):int(0.28 * h), int(0.72 * w):w]
            hsv_kf = cv2.cvtColor(kf_roi, cv2.COLOR_BGR2HSV)
            kf_red1 = cv2.inRange(hsv_kf, (0, 140, 120), (10, 255, 255))
            kf_red2 = cv2.inRange(hsv_kf, (170, 140, 120), (180, 255, 255))
            kf_red_count = cv2.countNonZero(kf_red1 | kf_red2)

            t_bucket = round(t * 2) / 2.0
            audio_e = energy_map.get(t_bucket, 0.0)

            # Strict elimination validation: genuine Kill Banner + combat audio confirmation
            has_red_banner = (red_count >= int(750 * scale) and audio_e >= 3000.0)
            has_gold_banner = (gold_count >= int(1000 * scale))
            is_headshot = kf_red_count >= int(350 * scale)

            if has_red_banner or has_gold_banner:
                # Debounce consecutive frames of the same banner (0.8s cooldown captures multi-kills)
                if t - last_kill_t >= 0.8:
                    moment = CombatMoment(
                        timestamp=t,
                        kill_count=1,
                        is_headshot=is_headshot,
                        audio_energy=audio_e,
                        is_player_kill=True
                    )
                    self.score_moment(moment)
                    combat_moments.append(moment)
                    last_kill_t = t

            frame_idx += step

        cap.release()

        # Build precision action windows
        action_windows = self.build_action_windows(
            combat_moments,
            total_duration=duration,
            lead_in=lead_in,
            lead_out=lead_out
        )

        total_score = sum(m.score for m in combat_moments)
        return CuratedHighlight(
            file_path=video_path,
            duration=duration,
            moments=combat_moments,
            action_windows=action_windows,
            total_score=total_score
        )
