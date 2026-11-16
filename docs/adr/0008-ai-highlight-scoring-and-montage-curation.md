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
1. **Multi-Signal Combat Detector**: Enhance `ValorantKillDetector` to analyze killfeed player bars (green/gold highlights), headshot icons, and audio frequency peaks corresponding to in-game kill chimes.
2. **Shot Quality Scorer**: Introduce `HighlightScorer` that evaluates moments based on kill count, headshot flag, and kill-chain proximity.
3. **Precision Action Window Trimming**: Modify `MontageCompositor` to pass `-ss <start> -to <end>` or FFmpeg `trim` filters per clip so only the actual combat action is assembled into the final reel.
4. **Multi-Format Montage Support**: Provide first-class 16:9 widescreen montage mode (no cropping, full cinematic display) alongside 9:16 vertical short mode.

## Consequences
- Clips without verified kills or combat action are excluded from montages by default.
- Final reels contain only high-adrenaline, beautiful shots stitched together with smooth pacing.
- Works across custom weapon skins and player settings without brittle hardcoded color failures.
