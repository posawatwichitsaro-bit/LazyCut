import os
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from sqlmodel import Session

from backend.app.core.config import settings
from backend.app.core.hardware_probe import get_ffmpeg_binary, get_best_hardware_encoder
from backend.app.core.safety import check_disk_safety
from backend.app.engine.filter_graph import build_9_16_filter_graph
from backend.app.models.entities import MontageJob, ReelExport, SourceClip

class MontageCompositor:
    def __init__(self, db_session: Session):
        self.session = db_session
        self.ffmpeg_bin = get_ffmpeg_binary()
        self.encoder = get_best_hardware_encoder()

    def execute_job(
        self,
        job_id: str,
        output_format: str = "9:16",
        bgm_path: str | Path | None = None
    ) -> ReelExport:
        """
        Executes a Montage Job, rendering selected clips into a final Reel.
        """
        job = self.session.get(MontageJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "PROCESSING"
        job.progress = 0.05
        self.session.commit()

        try:
            # 1. Parse selected clips
            clip_ids: list[str] = json.loads(job.selected_clips_json)
            if not clip_ids:
                raise ValueError("No clips selected for montage.")

            clips: list[SourceClip] = [self.session.get(SourceClip, cid) for cid in clip_ids if self.session.get(SourceClip, cid)]
            if not clips:
                raise ValueError("Selected clips not found in database.")

            # Load Vibe profile
            vibe_path = settings.vibes_dir / f"{job.vibe_id}.json"
            vibe_cfg = {}
            if vibe_path.exists():
                with open(vibe_path, "r", encoding="utf-8") as f:
                    vibe_cfg = json.load(f)

            ducking_cfg = vibe_cfg.get("audio_ducking", {})
            ducking_db = ducking_cfg.get("ducking_level_db", -14.0)
            fadeout_style = vibe_cfg.get("fadeout_style", "exp")
            fadeout_duration = vibe_cfg.get("fadeout_duration_seconds", 2.0)

            # 2. Pack clips within Duration Budget (capped at max 15 minutes)
            budget_limit = min(float(job.target_duration), float(settings.max_montage_duration_seconds))
            packed_clips: list[SourceClip] = []
            accumulated_duration = 0.0

            # Sort by kill count (highest first)
            sorted_clips = sorted(clips, key=lambda c: c.kill_count, reverse=True)
            for c in sorted_clips:
                c_dur = c.duration if c.duration > 0 else 10.0
                if accumulated_duration + c_dur <= budget_limit or not packed_clips:
                    packed_clips.append(c)
                    accumulated_duration += c_dur
                if accumulated_duration >= budget_limit:
                    break

            # 3. Disk Safety Guard verification
            est_output_bytes = int(accumulated_duration * 2.5 * 1024 * 1024)  # ~20 Mbps bitrate
            check_disk_safety(settings.exports_dir, est_output_bytes)

            job.progress = 0.20
            self.session.commit()

            # 4. Prepare FFmpeg inputs
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_filename = f"reel_{timestamp_str}_{job.id[:8]}.mp4"
            output_path = settings.exports_dir / output_filename

            input_args: list[str] = []
            chapters_lines: list[str] = [f"# LazyCut Reel - {timestamp_str}\n"]
            current_time = 0.0

            for idx, c in enumerate(packed_clips):
                input_args.extend(["-i", c.file_path])
                
                # Format timestamp MM:SS
                minutes = int(current_time // 60)
                seconds = int(current_time % 60)
                kills_str = f"({c.kill_count} Kills)" if c.kill_count > 0 else "(Action)"
                chapters_lines.append(f"{minutes:02d}:{seconds:02d} - Clip {idx + 1} {kills_str}")
                current_time += c.duration

            # Resolve BGM if requested
            bgm_present = False
            resolved_bgm = bgm_path or vibe_cfg.get("default_bgm_track")
            if resolved_bgm:
                bgm_file = Path(resolved_bgm)
                if not bgm_file.is_absolute():
                    bgm_file = settings.music_dir / resolved_bgm
                if bgm_file.exists():
                    input_args.extend(["-i", str(bgm_file)])
                    bgm_present = True

            job.progress = 0.35
            self.session.commit()

            # 5. Build Filter Graph (9:16 vertical layout + ducking)
            filter_script, final_v, final_a = build_9_16_filter_graph(
                clip_count=len(packed_clips),
                bgm_present=bgm_present,
                ducking_db=ducking_db,
                fadeout_style=fadeout_style,
                fadeout_duration=fadeout_duration,
                total_duration=accumulated_duration,
                preset_path=settings.presets_dir / f"{job.preset_id}.json"
            )

            job.progress = 0.50
            self.session.commit()

            # 6. Execute FFmpeg Command
            cmd = [
                self.ffmpeg_bin,
                "-y",
                *input_args,
                "-filter_complex", filter_script,
                "-map", final_v,
                "-map", final_a,
                "-c:v", self.encoder,
                "-preset", "fast",
                "-r", str(settings.default_fps),
                "-c:a", "aac",
                "-b:a", "192k",
                "-t", str(accumulated_duration),
                str(output_path)
            ]

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg encoding failed: {proc.stderr[-500:]}")

            # 7. Write Chapters File
            chapters_path = settings.exports_dir / f"chapters_{timestamp_str}_{job.id[:8]}.txt"
            chapters_content = "\n".join(chapters_lines)
            with open(chapters_path, "w", encoding="utf-8") as f:
                f.write(chapters_content)

            # 8. Create ReelExport Record
            export = ReelExport(
                job_id=job.id,
                output_path=str(output_path),
                actual_duration=round(accumulated_duration, 2),
                aspect_ratio=output_format,
                chapters_txt=chapters_content,
                ai_title=f"Valorant Highlights #{timestamp_str[:8]}",
                ai_description=f"Generated by LazyCut\n\nChapters:\n{chapters_content}"
            )
            self.session.add(export)

            job.status = "COMPLETED"
            job.progress = 1.0
            self.session.commit()
            self.session.refresh(export)
            return export

        except Exception as e:
            job.status = "FAILED"
            job.error_message = str(e)
            self.session.commit()
            raise
