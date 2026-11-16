# LazyCut Domain Model

A local-first, semi-automated video editing studio designed to turn short FPS gaming highlight clips into polished long-form and short-form reels.

## Language

**Source Clip**:
A pre-recorded video snippet (5 to 45 seconds) capturing a single gaming event or highlight.
_Avoid_: Raw Video, Raw VOD, Video Dump

**Reel**:
The final compiled and edited video ready for export or publishing (maximum duration: 15 minutes).
_Avoid_: Output, Final Render, Movie

**Game Preset**:
A configuration defining coordinate regions for cropping and layering gameplay and HUD elements into specific aspect ratios.
_Avoid_: Screen Config, Layout Template, Filter

**Vibe Profile**:
A configuration governing musical accompaniment, audio ducking, pacing, and transition behaviors.
_Avoid_: Theme, Style, Mood

**Montage Job**:
A discrete unit of work that processes a designated selection of Source Clips into a single Reel using a specified Game Preset and Vibe Profile.
_Avoid_: Task, Batch Run, Render Pipeline

**Killfeed Element**:
A designated screen region within a Game Preset displaying in-game elimination notifications used for event verification.
_Avoid_: Kill Box, Event Area

**Action Window**:
The trimmed time segment within a Source Clip encompassing the elimination event along with essential pre-kill setup and post-kill confirmation.
_Avoid_: Trimmed Segment, Sub-clip, Cut Range

**Disk Safety Guard**:
A pre-flight verification ensuring the target export drive has sufficient free storage (minimum 3x estimated output size or 2 GB threshold) before rendering begins.
_Avoid_: Space Checker, Storage Limit

**Game Process Guard**:
A toggleable background monitor that automatically pauses Montage Jobs while target game executables are actively running.
_Avoid_: Anti-Lag Monitor, Game Detector

**Kill-Chain Bridge**:
The contiguous preservation of multiple elimination events occurring within 4 seconds of each other in a Source Clip without cutting between them.
_Avoid_: Multi-kill Link, Chain Cut

**Zero-AI Fallback**:
The deterministic templating subsystem that produces titles, descriptions, and chapters when no AI provider is configured.
_Avoid_: Default Namer, Offline Mode

**Local-First Export**:
The architectural guarantee that all rendered Reels and chapter files are fully generated and saved to local storage before any publishing action.
_Avoid_: Pre-upload Cache, Local Dump

**Encoder Auto-Probe**:
The startup diagnostic routine that tests and selects the highest-performing available video encoder (NVENC, AMF, QSV, or libx264 fallback) with manual override support.
_Avoid_: GPU Checker, Driver Test

**Kill Verification Badge**:
A visual status indicator on a Source Clip indicating the presence and count of OpenCV-verified elimination events.
_Avoid_: Clip Tag, Status Marker
