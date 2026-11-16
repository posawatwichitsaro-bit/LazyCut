# ADR 0008: AI Highlight Scoring & Multi-Clip Montage Curation

## Status
Accepted

## Context
LazyCut's core promise is to turn raw gameplay recordings into exciting highlight reels by assembling only beautiful combat scenes (clean headshots, multi-kills, clutch shots), while completely discarding non-combat downtime (walking from spawn, buy phases, waiting).

The initial prototype relied on static color thresholds and center cropping without physically trimming out the non-combat dead time from input clips. To achieve true highlight curation:
1. Elimination events must be detected robustly across all custom weapon finishes (e.g. Champions, Kuronami, Prime) using multi-signal detection: killfeed player-highlight banners, headshot icons, and audio kill chimes.
2. Each detected moment must be scored based on "shot quality" (Headshots, Kill Chains, Flick speed).
3. The video assembly engine must physically slice the exact Action Window ($T_{kill} - 2.0s$ to $T_{kill} + 1.2s$) out of each clip, bridging chained kills and discarding all non-combat footage.
4. The compositor must support both 16:9 full-screen cinema montages and 9:16 vertical shorts.

## Decision
1. **Multi-Signal Combat Detector (Stage 1 Heuristic Filtering)**: Analyze killfeed player bars (green/gold highlights), weapon banner edge density, and 16kHz audio RMS energy peaks to rapidly detect candidate action windows across raw clips, completely discarding idle spawn walking.
2. **Chronological Timeline Sequencing**: Parse Outplayed and Project datetime patterns from filenames to arrange candidate highlights in exact chronological order (`before -> after`) to reflect the real progression of the match.
3. **AI Montage Director (Stage 2 AI Secondary Optimization)**: Use `AIMontageDirector` to query local Ollama (`qwen3.5-9B`, `qwen3.6`, `gemma4`) or deterministic pacing heuristics to fine-tune in/out cut points, assign transitions (cut vs crossfade), give weight to the final climax multi-kill, and generate narrative chapter titles.
4. **Precision Action Window Trimming**: Pass `-ss <start> -to <end>` per clip to FFmpeg so only the actual combat action is assembled into the final reel.
5. **Multi-Format Montage Support**: Provide first-class 16:9 widescreen montage mode (no cropping, full 1080p cinematic display) alongside 9:16 vertical short mode, hardware accelerated via RTX 5070 NVENC (`h264_nvenc`).

## Consequences
- Clips without verified kills or combat action are excluded from montages by default.
- Final reels contain only high-adrenaline, beautiful shots stitched together with smooth pacing.
- Works across custom weapon skins and player settings without brittle hardcoded color failures.
