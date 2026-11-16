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
  └── Automated Test Suite CI Coverage (35/35 Tests) ────── [x] Completed (100% Pass)
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
