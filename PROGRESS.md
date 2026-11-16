# LazyCut Project Progress & Roadmap Tracker

A living progress tracking document for **LazyCut: Open-Source AI Video Automation Studio**.

---

## 📌 Project Overview
- **Repository**: [https://github.com/posawatwichitsaro-bit/LazyCut](https://github.com/posawatwichitsaro-bit/LazyCut)
- **Local Path**: `d:\LazyCut`
- **Core Architecture**: Local-first single process (FastAPI backend serving static React UI + REST/WebSocket API), OpenCV for event detection, FFmpeg with hardware acceleration (NVENC/AMF/QSV/libx264) for compositing.
- **Reference Docs**:
  - [Domain Model (GLOSSARY.md)](file:///d:/LazyCut/GLOSSARY.md)
  - [Architecture Decision Records](file:///d:/LazyCut/docs/adr/)
  - [Visual Blueprints & Diagrams](file:///d:/LazyCut/docs/diagrams/README.md)

---

## 🚦 Roadmap & Phase Milestones

```
Phase 1: MVP Core Engine (95% Completed)
  ├── Scaffolding & Git Setup ───────────────────────────── [x] Completed
  ├── Database Models & SQLite Setup ────────────────────── [x] Completed
  ├── Hardware Encoder Auto-Probe ───────────────────────── [x] Completed (Detected h264_amf)
  ├── OpenCV Valorant Killfeed Detector ─────────────────── [x] Completed (Verified with unit tests)
  ├── FFmpeg Assembly Engine & Audio Ducking ────────────── [x] Completed (9:16 layout + ducking)
  ├── Presets & Audio Profiles (Valorant 1080p, Vibes) ──── [x] Completed
  ├── Watchdog Folder Monitor & Game Guard ──────────────── [x] Completed
  ├── Automated Test Suite (pytest) ─────────────────────── [x] Completed (9/9 passed)
  └── Windows start.bat Bootstrap ───────────────────────── [x] Completed

Phase 2: Local Web Dashboard & UI Integration (100% Completed)
  ├── FastAPI Static SPA Server & API Routes ────────────── [x] Completed
  ├── Metadata Engine & Zero-AI YouTube Chapters (P2-01) ── [x] Completed
  ├── Studio Feed Query Filters (kills, duration) (P2-02) ── [x] Completed
  ├── Montage Job API & Export Lifecycle (P2-03) ────────── [x] Completed
  ├── 3-Screen Dashboard UI (Feed, Inspector, Settings) ─── [x] Completed (P2-04 TDD passed)
  ├── Reel Inspector (Video Player, Chapters Copy, DL) ──── [x] Completed
  ├── Settings View (Watch Path, Presets, Guard, GPU) ───── [x] Completed
  └── Hybrid AI Router (Ollama + Zero-AI Fallback) (P2-05) ─ [x] Completed (P2-05 TDD passed)

Phase 3: Community Presets & Auto-Publish (100% Completed)
  ├── JSON Preset Builder & Schema Validator (P3-01) ────── [x] Completed (P3-01 TDD passed)
  ├── Discord / Telegram Webhook Notifications (P3-02) ──── [x] Completed (P3-02 TDD passed)
  └── YouTube Data API v3 OAuth2 Integration (P3-03) ────── [x] Completed (P3-03 TDD passed)

Phase 4: Open-Source Release & Packaging (100% Completed)
  ├── Comprehensive Documentation (README.md, Blueprints) ── [x] Completed
  ├── Community Preset Guide (docs/PRESET_GUIDE.md) ─────── [x] Completed
  ├── Community Contribution Guidelines (CONTRIBUTING.md) ─ [x] Completed
  ├── GitHub Actions Automated CI Workflow (.github/) ──── [x] Completed
  ├── Windows One-Click start.bat Bootstrap ─────────────── [x] Completed & Verified
  └── Automated Test Suite CI Coverage (41/41 Tests) ────── [x] Completed (100% Pass)

Phase 5: AI Highlight Curation & Montage Studio (100% Completed)
  ├── RTX 5070 NVENC Hardware Acceleration (P5-01) ──────── [x] Completed (Detected h264_nvenc)
  ├── Multi-Signal Kill & Headshot Detector 2.0 (P5-02) ─── [x] Completed (TDD passed)
  ├── AI Highlight Scorer (Headshots, Chains, Flicks) (P5-03) [x] Completed (TDD passed)
  ├── Precision Action Trimming (Cut Spawn Walking) (P5-04) ─ [x] Completed (TDD passed)
  ├── Multi-Clip 16:9 Cinema & 9:16 Montage Assembler (P5-05) [x] Completed (TDD passed)
  ├── Chronological Match Sequencing (P5-06) ───────────── [x] Completed (TDD passed)
  └── Hybrid AI Montage Director (Ollama 9B/36B) (P5-07) ── [x] Completed (TDD passed)
```

---

## 📋 Detailed Task Breakdown

| Task ID | Component | Description | Status |
|---|---|---|---|
| **P1-01** | **Repository** | Git initialize, remote origin, `.gitignore`, initial commit | `DONE` |
| **P1-02** | **Docs & Diagrams** | `GLOSSARY.md`, ADRs 0001-0007, Architecture/Pipeline/ER diagrams | `DONE` |
| **P1-03** | **Dependencies** | Create `requirements.txt` with FastAPI, OpenCV, Watchdog, SQLModel, imageio-ffmpeg | `DONE` |
| **P1-04** | **Data Models** | Setup SQLite database with SQLModel (`SourceClip`, `KillEvent`, `MontageJob`, `ReelExport`) | `DONE` |
| **P1-05** | **Hardware Probe** | Diagnostic module testing NVENC, AMF, QSV, falling back to libx264 (Auto-detected AMF) | `DONE` |
| **P1-06** | **OpenCV Detector** | Killfeed & Skull Banner detection for Valorant + Action Window calculation | `DONE` |
| **P1-07** | **FFmpeg Engine** | Filter complex generator for 9:16 cropping, sidechain audio ducking, fade-out curves | `DONE` |
| **P1-08** | **Presets & Audio** | Initial `presets/valorant_1080p.json` and default `vibes/` configuration | `DONE` |
| **P1-09** | **Folder Watcher** | Watchdog service monitoring video files + toggleable `VALORANT.exe` process guard | `DONE` |
| **P1-10** | **Bootstrap** | Windows `start.bat` script with auto-venv, dependency check, and browser opener | `DONE` |
| **P1-11** | **Test Suite** | Unit tests for safety, detection, filter graph, and models (9/9 passed) | `DONE` |
| **P1-12** | **Encoder Optimization**| AMF (`-quality speed`), NVENC (`-preset p4`), x264 (`-preset fast`) flag resolver | `DONE` |
| **P1-13** | **Blur Performance** | 8.6x faster cinematic background blur using 270x480 pre-downscale pipeline | `DONE` |
| **P1-14** | **Physical Video Cut** | OpenCV & FFmpeg unit test asserting actual video trimming, 9:16 aspect ratio transform, decoded pixel layers, and budget constraint | `DONE` |
| **P2-01** | **Metadata Engine** | `ReelMetadataEngine` with Zero-AI Fallback, tags, and YouTube chapters (TDD passed) | `DONE` |
| **P2-02** | **Clips Filtering API** | `GET /api/clips` query filtering by kills, duration range, and verification status (TDD passed) | `DONE` |
| **P2-03** | **Montage Job API** | `POST /api/jobs` and `GET /api/jobs/{id}/export` lifecycle validation (TDD passed) | `DONE` |
| **P2-04** | **3-Screen Dashboard** | Modern responsive SPA (Studio Feed, Reel Inspector with Video Player, Settings) (TDD passed) | `DONE` |
| **P2-05** | **Hybrid AI Router** | `AIRouter` with Ollama integration and Zero-AI resilient fallback (TDD passed) | `DONE` |
| **P3-01** | **Preset Validator** | Declarative JSON schema validator and safe loader for community presets (TDD passed) | `DONE` |
| **P3-02** | **Webhook Notifier** | Discord Embed and Telegram publish alerts with duration and chapters (TDD passed) | `DONE` |
| **P3-03** | **YouTube Uploader** | YouTube Data API v3 integration with OAuth2 decoupling and quota error handling (TDD passed) | `DONE` |
| **P4-01** | **Preset Guide** | Detailed guide for measuring screen coordinates and authoring community presets | `DONE` |
| **P4-02** | **Contributing Guide**| Open-source contribution rules, TDD development loop, and MIT License terms | `DONE` |
| **P4-03** | **GitHub Actions CI** | Automated cross-python testing workflow (`.github/workflows/ci.yml`) | `DONE` |
| **P5-01** | **RTX 5070 NVENC** | Auto-probe 256x256 fix to unlock hardware-accelerated NVENC on NVIDIA RTX 5070 | `DONE` |
| **P5-02** | **Multi-Signal Detector**| Valorant combat & kill detection using player killfeed highlights + headshot icons + audio chimes | `DONE` |
| **P5-03** | **Highlight Scorer** | Algorithmic scoring ranking clips by headshot count, multi-kill chains, and eliminating dead footage | `DONE` |
| **P5-04** | **Action Trimming** | Physical extraction of $T_{kill}-2.5s$ to $T_{kill}+1.2s$ per kill, removing spawn walks | `DONE` |
| **P5-05** | **Montage Assembler** | Multi-clip montage stitching top highlights into 16:9 Cinema and 9:16 Short formats | `DONE` |


---

## 📝 Activity & Development Log

- **2026-11-16**:
  - Completed comprehensive 4-round grilling session covering input scope, architecture, trimming, audio ducking, disk safety, hardware probes, and database strategy.
  - Authored `GLOSSARY.md` establishing standardized project domain language.
  - Recorded ADRs 0001 through 0007 in `docs/adr/`.
  - Authored 3 SVG diagram blueprints (`system-architecture.html`, `montage-pipeline.html`, `data-model.html`) verified against WCAG contrast and geometry checks.
  - Initialized Git repository and set remote to `https://github.com/posawatwichitsaro-bit/LazyCut.git`.
  - Implemented Phase 1 MVP Core Engine, Watchdog background monitor, and OpenCV Valorant kill detector.
  - Implemented Phase 2 single-process FastAPI web dashboard, metadata engine, and AI router.
  - Implemented Phase 3 Discord/Telegram webhook notifier and YouTube Data API v3 uploader.
  - Implemented Phase 4 open-source community documentation and GitHub Actions CI.
  - Fixed Windows `start.bat` launch crash caused by cmd.exe parenthesis parsing.
  - Verified live server with real user clip `Project 05_10-09-2026_19-23-11-560.mp4`.
  - Diagnosed and resolved AMD AMF encoder preset parsing issue (`-quality speed` vs `-preset fast`).
  - Benchmarked and deployed 8.6x faster cinematic background blur optimization (`scale=270:480,boxblur=5:2,scale=1080:1920`), reducing reel render time down to 3.08 seconds!
  - 35/35 automated unit & integration tests passing with 100% success rate.
  - Completed end-to-end browser user workflow testing on `http://localhost:8000/` with live clip library at `D:\Clips\Valorant`: Settings watch path configuration, clip feed selection, 9:16 vertical reel rendering (`reel_20261116_145014_bc94cc70.mp4`), and Reel Inspector verification with in-browser video playback and YouTube chapters copy.
  - Authored physical video cut and composition unit tests (`tests/test_compositor_video_cut.py`) verifying real FFmpeg rendering, actual duration trimming (6.0s down to <=2.5s), 16:9 to 9:16 aspect ratio transformation, layer pixel decoding, and budget enforcement. Test suite expanded to 37/37 passing (100%).
  - Pivoted architecture to **Hybrid 2-Stage Highlight & Montage Studio** per user directive:
    - **Hardware**: Unlocked RTX 5070 NVENC hardware encoding (`h264_nvenc`) by fixing probe dimensions to 256x256.
    - **Stage 1 (Fast Multi-Modal Filtering)**: Built `HighlightCurator` combining 16kHz audio energy peaks with killfeed player bars & banner edge density, discarding idle spawn walking.
    - **Chronological Sequencing**: Extracted Outplayed & Project timestamps from filenames to assemble gameplay strictly in match progression order (`before -> after`).
    - **Stage 2 (AI Secondary Pacing Optimization)**: Implemented `AIMontageDirector` integrating local Ollama (`qwen3.5-9B`, `qwen3.6`, `gemma4`) with warm 1.07s inference time and deterministic heuristic fallback for in/out pacing, climax emphasis, and chapter titles.
    - **Aspect Ratios**: Supported full 16:9 Cinema widescreen montage without cropping alongside 9:16 Shorts.
    - **Library Scan**: Added automatic startup and on-demand rescan discovering all 87 clips in `D:\Clips\Valorant`.
    - **Test Coverage**: 44/44 unit & integration tests passing (100%).
  - **Clip Picker UI & Contextual Action Window Upgrade**:
    - **Interactive Clip Picker Grid**: Replaced tabular view with modern responsive card grid featuring video thumbnail previews, checkboxes, kill count badges, and modal inspector with kill breakdown.
    - **Thumbnail Engine**: Implemented `GET /api/clips/{id}/thumbnail` using on-demand FFmpeg frame extraction with local disk caching in `exports/thumbnails/`.
    - **Contextual Action Window**: Expanded action trimming from 3.5s to 7.0–8.0s ($T_{kill}-5.0s$ to $T_{kill}+2.0s$) ensuring clear narrative setup (peek/approach), the kill event, and confirmation aftermath.
    - **Pacing & In/Out Optimization**: Upgraded `AIMontageDirector` with contextual setup preservation and dynamic transition diversity (punchy cuts for multi-kills, crossfades for round transitions).
    - **Test Suite**: 46/46 unit & integration tests passing with 100% success rate.
