import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from sqlmodel import Session

from backend.app.core.config import settings
from backend.app.core.hardware_probe import get_ffmpeg_binary, get_best_hardware_encoder, get_encoder_optimization_args
from backend.app.core.safety import check_disk_safety
from backend.app.engine.filter_graph import build_9_16_filter_graph, build_16_9_cinema_filter_graph
from backend.app.detection.clip_analysis import EventSelection, HighlightTiming, analyze_clip, highlight_result
from backend.app.engine.ai_montage_director import CandidateCut, OptimizedCut
from backend.app.models.entities import MontageJob, ReelExport, SourceClip
from backend.app.watcher.process_guard import is_game_process_running

def plan_cuts(candidates: list[CandidateCut], budget: float) -> list[OptimizedCut]:
    ranked = sorted(
        candidates,
        key=lambda cut: (-cut.kills, not cut.is_headshot, -cut.energy, cut.chronological_key, cut.raw_start),
    )
    selected = []
    for cut in ranked:
        start, end = round(cut.raw_start, 2), round(cut.raw_end, 2)
        duration = min(round(end - start, 2), round(budget, 2))
        if duration < 0.5:
            continue

        if duration < end - start:
            anchor = cut.event_times[0] if cut.event_times else start
            start = round(max(start, min(anchor - duration / 2, end - duration)), 2)
            end = round(start + duration, 2)

        kills = sum(start <= timestamp < end for timestamp in cut.event_times)
        if cut.event_times and not kills:
            continue
        selected.append((cut.chronological_key, start, end, cut, kills))
        budget -= duration

    selected.sort(key=lambda item: (item[0], item[3].file_name, item[1]))
    return [
        OptimizedCut(
            clip_id=cut.clip_id, file_name=cut.file_name, start=start, end=end,
            title=f"Clip {index} ({kills} {'Kill' if kills == 1 else 'Kills'})",
            kills=kills,
        )
        for index, (_, start, end, cut, kills) in enumerate(selected, 1)
    ]


class MontageCompositor:
    def __init__(self, db_session: Session):
        self.session = db_session
        self.ffmpeg_bin = get_ffmpeg_binary()
        self.encoder = get_best_hardware_encoder()

    def execute_job(
        self,
        job_id: str,
        output_format: str = "9:16",
        bgm_path: str | Path | None = None,
        timing: HighlightTiming | None = None,
        selections: dict[str, EventSelection] | None = None,
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
            if is_game_process_running():
                raise ValueError("Game Process Guard is active. Close the game before rendering.")

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

            timing = timing or HighlightTiming()
            selections = selections or {}
            candidate_cuts: list[CandidateCut] = []
            fallback_cuts: list[CandidateCut] = []
            clip_map = {clip.id: clip for clip in clips}

            for clip in clips:
                selection = selections.get(clip.id)
                if not Path(clip.file_path).is_file():
                    if selection is not None:
                        raise ValueError(f"Selected source clip is missing: {clip.file_name}")
                    continue

                moments, revision = analyze_clip(self.session, clip)
                if selection is not None:
                    if selection.revision != revision:
                        raise ValueError(f"Analysis changed for {clip.file_name}. Reopen Preview and select events again.")
                    indices = sorted(set(selection.event_indices))
                    if any(index < 0 or index >= len(moments) for index in indices):
                        raise ValueError(f"Invalid event selection for {clip.file_name}.")
                    moments = [moments[index] for index in indices]

                result = highlight_result(clip, moments, timing)
                for start, end in result.action_windows:
                    events = sorted(
                        (m for m in moments if start <= m.timestamp < end),
                        key=lambda m: (-m.score, m.timestamp),
                    )
                    if events:
                        candidate_cuts.append(CandidateCut(
                            clip_id=clip.id, file_name=clip.file_name,
                            raw_start=start, raw_end=end, kills=len(events),
                            is_headshot=any(m.is_headshot for m in events),
                            energy=max(m.audio_energy for m in events),
                            event_times=tuple(m.timestamp for m in events),
                        ))

                if selection is None and not moments and clip.duration > 0:
                    fallback_cuts.append(CandidateCut(
                        clip_id=clip.id, file_name=clip.file_name,
                        raw_start=0.0, raw_end=clip.duration, kills=0,
                    ))

            if not candidate_cuts and not selections:
                candidate_cuts = fallback_cuts

            budget_limit = min(job.target_duration, settings.max_montage_duration_seconds)
            optimized_edl = plan_cuts(candidate_cuts, budget_limit)
            accumulated_duration = sum(cut.duration for cut in optimized_edl)

            if not optimized_edl:
                raise ValueError("No valid cuts could be assembled.")

            packed_clips = [
                clip_map[cut.clip_id].model_copy(update={"duration": cut.duration, "kill_count": cut.kills})
                for cut in optimized_edl
            ]

            # 4. Disk Safety Guard verification
            est_output_bytes = int(accumulated_duration * 2.5 * 1024 * 1024)  # ~20 Mbps bitrate
            check_disk_safety(settings.exports_dir, est_output_bytes)

            job.progress = 0.20
            self.session.commit()

            # 5. Prepare FFmpeg inputs in exact chronological timeline order
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_filename = f"reel_{timestamp_str}_{job.id[:8]}.mp4"
            output_path = settings.exports_dir / output_filename

            input_args: list[str] = []
            chapters_lines: list[str] = [f"# LazyCut Reel - {timestamp_str}\n"]
            current_time = 0.0

            for idx, cut in enumerate(optimized_edl):
                c = clip_map[cut.clip_id]
                # Precision action slicing with sample-exact seeking and negative timestamp avoidance
                input_args.extend([
                    "-ss", f"{cut.start:.2f}",
                    "-to", f"{cut.end:.2f}",
                    "-accurate_seek",
                    "-avoid_negative_ts", "make_zero",
                    "-i", c.file_path
                ])
                
                # Format timestamp MM:SS
                minutes = int(current_time // 60)
                seconds = int(current_time % 60)
                chapters_lines.append(f"{minutes:02d}:{seconds:02d} - {cut.title or f'Clip {idx + 1}'}")
                current_time += cut.duration

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

            # 6. Build Filter Graph (16:9 Cinema or 9:16 Vertical)
            if output_format == "16:9":
                filter_script, final_v, final_a = build_16_9_cinema_filter_graph(
                    clip_count=len(optimized_edl),
                    bgm_present=bgm_present,
                    ducking_db=ducking_db,
                    fadeout_style=fadeout_style,
                    fadeout_duration=fadeout_duration,
                    total_duration=accumulated_duration
                )
            else:
                filter_script, final_v, final_a = build_9_16_filter_graph(
                    clip_count=len(optimized_edl),
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
            opt_args = get_encoder_optimization_args(self.encoder)
            cmd = [
                self.ffmpeg_bin,
                "-y",
                *input_args,
                "-filter_complex", filter_script,
                "-map", final_v,
                "-map", final_a,
                "-c:v", self.encoder,
                *opt_args,
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

            # 7. Generate Creative Metadata & Chapters via AIRouter
            from backend.app.engine.ai_router import AIRouter
            ai_router = AIRouter(provider="none")  # Extensible with settings.ai_provider
            ai_meta = ai_router.generate(job=job, clips=packed_clips)

            chapters = "\n".join(chapters_lines) + "\n"
            chapters_path = settings.exports_dir / f"chapters_{timestamp_str}_{job.id[:8]}.txt"
            with open(chapters_path, "w", encoding="utf-8") as f:
                f.write(chapters)

            # 8. Create ReelExport Record
            export = ReelExport(
                job_id=job.id,
                output_path=str(output_path),
                actual_duration=round(accumulated_duration, 2),
                aspect_ratio=output_format,
                chapters_txt=chapters,
                ai_title=ai_meta.title,
                ai_description=ai_meta.description.replace(ai_meta.chapters_txt, chapters.rstrip())
            )
            self.session.add(export)

            # 9. Send Notifications (Discord / Telegram) if configured
            if settings.discord_webhook_url:
                try:
                    from backend.app.engine.notifier import WebhookNotifier
                    notifier = WebhookNotifier()
                    notifier.send_discord(settings.discord_webhook_url, export)
                except Exception as e:
                    pass

            job.status = "COMPLETED"
            job.progress = 1.0
            self.session.commit()
            self.session.refresh(export)
            return export

        except Exception as e:
            self.session.rollback()
            job.status = "FAILED"
            job.error_message = str(e)
            self.session.commit()
            raise
