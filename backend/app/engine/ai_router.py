import json
import logging
import httpx
from dataclasses import dataclass
from backend.app.models.entities import SourceClip, MontageJob
from backend.app.engine.metadata_engine import ReelMetadataEngine, ReelMetadataResult

logger = logging.getLogger("lazycut.ai_router")

@dataclass
class AIMetadataResponse:
    title: str
    description: str
    tags: list[str]
    chapters_txt: str
    is_fallback: bool = False

class AIRouter:
    def __init__(
        self,
        provider: str = "none",  # "none", "ollama", "openai", "gemini", "claude"
        base_url: str = "http://localhost:11434",
        api_key: str | None = None,
        model: str = "llama3.2"
    ):
        self.provider = provider.lower()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.fallback_engine = ReelMetadataEngine()

    def generate(
        self,
        job: MontageJob,
        clips: list[SourceClip]
    ) -> AIMetadataResponse:
        """
        Attempts to generate creative AI metadata via the configured provider.
        Gracefully falls back to deterministic Zero-AI templates on any error.
        """
        # Always generate baseline Zero-AI fallback & chapters
        baseline: ReelMetadataResult = self.fallback_engine.generate_metadata(job, clips)
        fallback_resp = AIMetadataResponse(
            title=baseline.title,
            description=baseline.description,
            tags=baseline.tags,
            chapters_txt=baseline.chapters_txt,
            is_fallback=True
        )

        if self.provider == "none":
            return fallback_resp

        total_kills = sum(c.kill_count for c in clips)
        game_name = "Valorant"
        if "valorant" in job.preset_id.lower():
            game_name = "Valorant"

        prompt = (
            f"You are a gaming highlight video creator. Generate catchy YouTube Shorts / TikTok metadata "
            f"for a {game_name} montage with {total_kills} total kills across {len(clips)} action clips in {job.vibe_id} style.\n"
            f"Respond ONLY with a valid JSON object matching this schema:\n"
            f'{{"title": "Punchy Catchy Title with emoji", "description": "Engaging 1-2 sentence description", "tags": ["#Tag1", "#Tag2", "#Tag3"]}}'
        )

        try:
            if self.provider == "ollama":
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "format": "json",
                            "stream": False
                        }
                    )
                    if resp.status_code == 200:
                        raw_data = resp.json().get("response", "")
                        parsed = json.loads(raw_data)
                        return AIMetadataResponse(
                            title=parsed.get("title", baseline.title),
                            description=parsed.get("description", baseline.description),
                            tags=parsed.get("tags", baseline.tags),
                            chapters_txt=baseline.chapters_txt,
                            is_fallback=False
                        )
        except Exception as e:
            logger.warning(f"AI Router generation failed ({e}). Using Zero-AI Fallback.")

        return fallback_resp
