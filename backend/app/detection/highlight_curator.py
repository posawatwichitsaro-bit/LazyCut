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
            score += 25.0  # High audio excitement
        
        moment.score = score
        return score

    def is_worth_keeping(self, moment: CombatMoment) -> bool:
        return self.score_moment(moment) >= 50.0

    def build_action_windows(
        self,
        moments: list[CombatMoment],
        total_duration: float,
        lead_in: float = 5.0,
        lead_out: float = 2.0,
        bridge_threshold: float = 4.0
    ) -> list[tuple[float, float]]:
        """
        Calculates precision action windows around confirmed combat moments.
        Bridges moments occurring within bridge_threshold (e.g. 4.0s).
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
            windows.append((start, end))

        # Score each action window based on the combat moments it contains
        scored_windows: list[tuple[tuple[float, float], float]] = []
        for w_start, w_end in windows:
            w_score = sum(m.score for m in valid_moments if w_start <= m.timestamp <= w_end)
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
        lead_in: float = 5.0,
        lead_out: float = 2.0
    ) -> CuratedHighlight:
        """
        Scans a video file, combining audio combat energy with kill visual cues.
        Returns a CuratedHighlight with precision Action Windows and shot scores.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open clip: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if total_frames > 0 else 0.0
        cap.release()

        # 1. Audio combat peaks
        audio_peaks = self.extract_audio_peaks(video_path)
        if not audio_peaks:
            return CuratedHighlight(video_path, duration, [], [], 0.0)

        # Baseline energy and peak threshold
        energies = [p[1] for p in audio_peaks]
        mean_energy = float(np.mean(energies)) if energies else 1000.0
        max_energy = float(np.max(energies)) if energies else 1000.0
        peak_threshold = max(3500.0, mean_energy * 1.5)

        # 2. Visual scan around high-energy windows
        # Sample frames around energy peaks
        combat_moments: list[CombatMoment] = []
        cap = cv2.VideoCapture(str(video_path))

        for t, energy in audio_peaks:
            if energy >= peak_threshold:
                # Inspect frame at timestamp t
                frame_idx = int(t * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    continue

                h, w = frame.shape[:2]
                
                # Check killfeed (top right: x=0.75*w .. w, y=0.03*h .. 0.30*h)
                kf_roi = frame[int(0.03 * h):int(0.30 * h), int(0.70 * w):w]
                
                # Check lower center banner (y=0.70*h .. 0.92*h, x=0.40*w .. 0.60*w)
                banner_roi = frame[int(0.70 * h):int(0.92 * h), int(0.40 * w):int(0.60 * w)]

                # Detect combat activity:
                # Check for green/teal player bar in killfeed (Hue 65..95)
                hsv_kf = cv2.cvtColor(kf_roi, cv2.COLOR_BGR2HSV)
                green_mask = cv2.inRange(hsv_kf, np.array([65, 80, 80]), np.array([95, 255, 255]))
                green_pixels = cv2.countNonZero(green_mask)

                # Check for red headshot / elimination icon in killfeed
                red_mask1 = cv2.inRange(hsv_kf, np.array([0, 120, 120]), np.array([10, 255, 255]))
                red_mask2 = cv2.inRange(hsv_kf, np.array([170, 120, 120]), np.array([180, 255, 255]))
                red_kf_pixels = cv2.countNonZero(red_mask1 | red_mask2)

                # Check bottom center banner emblem edges
                banner_edges = cv2.countNonZero(cv2.Canny(banner_roi, 50, 150))

                # Local player kill criteria: prominent green bar in killfeed + kill banner emblem
                # Scale threshold with ROI resolution
                roi_scale = (h * w) / (1080.0 * 1920.0)
                min_green = int(4000 * roi_scale)
                min_banner_edges = int(4500 * roi_scale)

                is_kill = (green_pixels >= min_green) or (green_pixels >= int(min_green * 0.25) and banner_edges >= min_banner_edges)
                is_headshot = red_kf_pixels > int(500 * roi_scale)

                if is_kill:
                    # Estimate kill count from green bars
                    kill_count = 2 if green_pixels >= min_green else 1
                    moment = CombatMoment(
                        timestamp=t,
                        kill_count=kill_count,
                        is_headshot=is_headshot,
                        audio_energy=energy,
                        is_player_kill=True
                    )
                    self.score_moment(moment)
                    combat_moments.append(moment)

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
