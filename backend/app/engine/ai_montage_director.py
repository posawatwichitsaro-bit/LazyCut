import re
import json
import logging
import urllib.request
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("lazycut.ai_director")

def parse_clip_chronological_key(file_name_or_path: str) -> float:
    """
    Extracts a chronological timestamp float from video filenames or metadata.
    Supports Outplayed format: Valorant_MM-DD-YYYY_HH-MM-SS-X.mp4
    And Project format: Project XX_DD-MM-YYYY_HH-MM-SS.mp4
    """
    name = Path(file_name_or_path).name

    # 1. Outplayed: Valorant_11-22-2024_15-40-51-0.mp4
    outplayed_match = re.search(r"Valorant_(\d{1,2})-(\d{1,2})-(\d{4})_(\d{1,2})-(\d{1,2})-(\d{1,2})", name, re.IGNORECASE)
    if outplayed_match:
        m, d, y, hh, mm, ss = map(int, outplayed_match.groups())
        try:
            dt = datetime(y, m, d, hh, mm, ss)
            return dt.timestamp()
        except ValueError:
            pass

    # 2. Project format: Project 05_10-09-2026_19-23-11-560.mp4
    project_match = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})_(\d{1,2})-(\d{1,2})-(\d{1,2})", name)
    if project_match:
        d, m, y, hh, mm, ss = map(int, project_match.groups())
        try:
            dt = datetime(y, m, d, hh, mm, ss)
            return dt.timestamp()
        except ValueError:
            pass

    # Fallback to filesystem modification time if file exists
    p = Path(file_name_or_path)
    if p.exists():
        return p.stat().st_mtime

    return 0.0

class CandidateCut:
    def __init__(
        self,
        clip_id: str,
        file_name: str,
        raw_start: float,
        raw_end: float,
        kills: int = 1,
        is_headshot: bool = False,
        energy: float = 5000.0,
        event_times: tuple[float, ...] = (),
    ):
        self.clip_id = clip_id
        self.file_name = file_name
        self.raw_start = raw_start
        self.raw_end = raw_end
        self.raw_duration = max(1.0, raw_end - raw_start)
        self.kills = kills
        self.is_headshot = is_headshot
        self.energy = energy
        self.event_times = event_times
        self.chronological_key = parse_clip_chronological_key(file_name)

class OptimizedCut:
    def __init__(
        self,
        clip_id: str,
        file_name: str,
        start: float,
        end: float,
        transition: str = "cut",
        title: str = "",
        kills: int = 0,
    ):
        self.clip_id = clip_id
        self.file_name = file_name
        self.start = round(start, 2)
        self.end = round(end, 2)
        self.duration = round(max(0.5, end - start), 2)
        self.transition = transition
        self.title = title
        self.kills = kills

    def to_dict(self) -> dict:
        return {
            "clip_id": self.clip_id,
            "file_name": self.file_name,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "transition": self.transition,
            "title": self.title
        }

class AIMontageDirector:
    """
    Hybrid AI Montage Director:
    1. Sequences candidate highlight cuts in strict chronological order (before -> after).
    2. Utilizes secondary AI optimization (Ollama LLM or intelligent heuristic fallback)
       to fine-tune cut timings, pacing build-up, and transition choices.
    """
    def __init__(self, ollama_url: str = "http://localhost:11434", enable_llm: bool = True):
        self.ollama_url = ollama_url
        self.enable_llm = enable_llm

    def _resolve_ollama_model(self) -> str | None:
        """Finds the best responsive local model in Ollama."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "") for m in data.get("models", [])]
                if not models:
                    return None
                
                # Priority: fast GPU-resident models first, then general models
                preferred_order = [
                    "srchmnmichael/qwen3.5-9B-uncensored:latest",
                    "gemma4:latest",
                    "gemma4:12b",
                    "s1gnature/gemma4-uncensored-mtp:e2b-q4_k_m",
                    "qwen3.6:latest",
                    "orcarouter/Qwen3.8-27B-Uncensored:latest",
                ]
                for pref in preferred_order:
                    if pref in models:
                        return pref
                return models[0]
        except Exception:
            return None

    def sort_chronologically(self, cuts: list[CandidateCut]) -> list[CandidateCut]:
        """Arranges candidate cuts in exact match chronological timeline order."""
        return sorted(cuts, key=lambda c: (c.chronological_key, c.raw_start))

    def optimize_edl(
        self,
        candidate_cuts: list[CandidateCut],
        target_budget: float = 60.0
    ) -> list[OptimizedCut]:
        """
        Takes candidate cuts, ensures chronological order, and refines in/out points
        so pacing builds momentum towards the final climax clip.
        """
        if not candidate_cuts:
            return []

        # Step 1: Arrange strictly from earliest to latest in match timeline
        chrono_cuts = self.sort_chronologically(candidate_cuts)

        # Step 2: Attempt LLM-based secondary optimization via Ollama if enabled
        if self.enable_llm:
            llm_optimized = self._query_ollama_optimizer(chrono_cuts, target_budget)
            if llm_optimized:
                logger.info(f"Ollama AI Director successfully optimized {len(llm_optimized)} cuts")
                return llm_optimized

        # Step 3: High-precision deterministic secondary optimization (Fallback)
        return self._heuristic_secondary_optimizer(chrono_cuts, target_budget)

    def _heuristic_secondary_optimizer(
        self,
        chrono_cuts: list[CandidateCut],
        target_budget: float
    ) -> list[OptimizedCut]:
        """
        Intelligent secondary pacing optimizer:
        - Allocates more screen time to multi-kill / clutch highlights (climax)
        - Snaps early buildup clips to tight, punchy action windows
        - Keeps overall duration within target_budget
        """
        total_raw = sum(c.raw_duration for c in chrono_cuts)
        scale_factor = min(1.0, target_budget / total_raw) if total_raw > 0 else 1.0

        optimized: list[OptimizedCut] = []
        accumulated = 0.0

        for idx, cut in enumerate(chrono_cuts):
            is_last = (idx == len(chrono_cuts) - 1)
            # Give multi-kill climax moments 1.20x pacing weight
            pacing_weight = 1.20 if (cut.kills >= 2 or is_last) else 0.95
            # Prioritize readability: minimum 3.5s per engagement unless raw clip is shorter
            min_readable = min(3.5, cut.raw_duration)
            desired_dur = min(cut.raw_duration, max(min_readable, cut.raw_duration * scale_factor * pacing_weight))

            if accumulated + desired_dur > target_budget:
                remaining = target_budget - accumulated
                if remaining < 0.8:
                    if not optimized:
                        desired_dur = max(0.5, target_budget)
                    else:
                        break
                else:
                    desired_dur = remaining

            # Preserve the contextual setup (peek) and aftermath (confirmation)
            if desired_dur >= cut.raw_duration:
                opt_start = cut.raw_start
                opt_end = cut.raw_end
            else:
                # Give 60% of duration to setup & kill, 40% to aftermath
                midpoint = (cut.raw_start + cut.raw_end) / 2.0
                opt_start = max(cut.raw_start, midpoint - (desired_dur * 0.60))
                opt_end = opt_start + desired_dur

            # Diverse transition design: punchy cuts for multi-kills, smooth crossfades for round breaks
            if cut.kills >= 2 or is_last:
                transition = "cut"
            elif idx % 2 == 1:
                transition = "crossfade"
            else:
                transition = "cut"

            kills_label = f"({cut.kills} Kills)" if cut.kills > 0 else "(Highlight)"
            title = f"Clip {idx + 1} {kills_label}"

            opt_cut = OptimizedCut(
                clip_id=cut.clip_id,
                file_name=cut.file_name,
                start=opt_start,
                end=opt_end,
                transition=transition,
                title=title
            )
            optimized.append(opt_cut)
            accumulated += opt_cut.duration

            if accumulated >= target_budget:
                break

        return optimized

    def _query_ollama_optimizer(
        self,
        chrono_cuts: list[CandidateCut],
        target_budget: float
    ) -> list[OptimizedCut] | None:
        """Queries local Ollama to fine-tune pacing and chapters."""
        try:
            model = self._resolve_ollama_model()
            if not model:
                return None

            cuts_meta = [
                {
                    "clip_id": c.clip_id,
                    "file": c.file_name,
                    "raw_start": c.raw_start,
                    "raw_end": c.raw_end,
                    "duration": c.raw_duration,
                    "kills": c.kills,
                    "headshot": c.is_headshot
                }
                for c in chrono_cuts
            ]

            prompt = (
                f"You are an expert esports montage director. Given candidate gameplay cuts in chronological order:\n"
                f"{json.dumps(cuts_meta)}\n"
                f"Optimize each cut to fit within {target_budget}s total budget. Ensure each cut has clear narrative context (approach/peek setup, kill moment, confirmation). "
                f"Design varied in/out pacing (punchy for multi-kills, cinematic for openers) and build hype towards the climax.\n"
                f"Respond with JSON format: {{\"cuts\": [ {{\"clip_id\": str, \"start\": float, \"end\": float, \"transition\": \"cut\"|\"crossfade\", \"title\": str}} ] }}"
            )

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }

            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                data = json.loads(resp.read().decode())
                resp_json = json.loads(data.get("response", "{}"))
                cuts_list = resp_json.get("cuts", [])
                if cuts_list and len(cuts_list) == len(chrono_cuts):
                    return [
                        OptimizedCut(
                            clip_id=item["clip_id"],
                            file_name=chrono_cuts[i].file_name,
                            start=float(item["start"]),
                            end=float(item["end"]),
                            transition=item.get("transition", "cut"),
                            title=item.get("title", f"Clip {i+1}")
                        )
                        for i, item in enumerate(cuts_list)
                    ]
        except Exception as e:
            logger.debug(f"Ollama optimization bypassed: {e}")
        return None
