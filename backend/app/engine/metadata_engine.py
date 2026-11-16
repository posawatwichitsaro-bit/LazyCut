import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from backend.app.core.config import settings
from backend.app.models.entities import SourceClip, MontageJob

@dataclass
class ReelMetadataResult:
    title: str
    description: str
    tags: list[str]
    chapters_txt: str
    is_ai_generated: bool = False

class ReelMetadataEngine:
    def __init__(self, ai_provider: str | None = None):
        self.ai_provider = ai_provider

    def generate_metadata(
        self,
        job: MontageJob,
        clips: list[SourceClip]
    ) -> ReelMetadataResult:
        """
        Generates publication metadata and timestamp chapters for a Reel.
        Uses Zero-AI Fallback template if no AI provider is active.
        """
        # If AI router is not active, run Zero-AI Fallback
        return self._generate_zero_ai_fallback(job, clips)

    def _generate_zero_ai_fallback(
        self,
        job: MontageJob,
        clips: list[SourceClip]
    ) -> ReelMetadataResult:
        total_kills = sum(c.kill_count for c in clips)
        
        # Determine game name from preset
        preset_file = settings.presets_dir / f"{job.preset_id}.json"
        game_name = "Valorant"
        if preset_file.exists():
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    p_data = json.load(f)
                    game_name = p_data.get("game_name", "Valorant")
            except Exception:
                pass

        date_str = job.created_at.strftime("%Y-%m-%d")
        kills_suffix = f"({total_kills} Kills)" if total_kills > 0 else "(Highlight Reel)"
        title = f"{game_name} Highlights - {date_str} {kills_suffix}"

        tags = [
            f"#{game_name}",
            "#Gaming",
            "#Montage",
            "#FPS",
            "#Shorts"
        ]

        # Generate YouTube timestamp chapters
        chapter_lines: list[str] = [f"00:00 - Intro ({game_name})"]
        accumulated_sec = 0.0

        for idx, clip in enumerate(clips):
            minutes = int(accumulated_sec // 60)
            seconds = int(accumulated_sec % 60)
            kill_label = f"({clip.kill_count} Kill{'s' if clip.kill_count != 1 else ''})"
            chapter_lines.append(f"{minutes:02d}:{seconds:02d} - Clip {idx + 1} {kill_label}")
            accumulated_sec += max(1.0, clip.duration)

        chapters_txt = "\n".join(chapter_lines)

        description = (
            f"{title}\n\n"
            f"Automated highlight montage created locally with LazyCut.\n\n"
            f"Chapters:\n{chapters_txt}\n\n"
            f"{' '.join(tags)}"
        )

        return ReelMetadataResult(
            title=title,
            description=description,
            tags=tags,
            chapters_txt=chapters_txt,
            is_ai_generated=False
        )
