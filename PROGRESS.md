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

Phase 3: Community Presets & Auto-Publish (80% Completed)
  ├── JSON Preset Builder & Schema Validator (P3-01) ────── [x] Completed (P3-01 TDD passed)
  ├── Discord / Telegram Webhook Notifications (P3-02) ──── [x] Completed (P3-02 TDD passed)
  └── YouTube Data API v3 OAuth2 Integration ────────────── [/] Export Ready / BYOC Stub

Phase 4: Open-Source Release & Packaging (In Progress)
  ├── Comprehensive Documentation (README.md, Blueprints) ── [x] Completed
  ├── Windows One-Click start.bat Bootstrap ─────────────── [x] Completed & Verified
  ├── Automated Test Suite CI Coverage (30/30 Tests) ────── [x] Completed (100% Pass)
  └── Community Contribution Guidelines (MIT License) ──── [x] Completed
```

---

## 📋 Detailed Task Breakdown (Phase 1)

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
| **P2-01** | **Metadata Engine** | `ReelMetadataEngine` with Zero-AI Fallback, tags, and YouTube chapters (TDD passed) | `DONE` |
| **P2-02** | **Clips Filtering API** | `GET /api/clips` query filtering by kills, duration range, and verification status (TDD passed) | `DONE` |
| **P2-03** | **Montage Job API** | `POST /api/jobs` and `GET /api/jobs/{id}/export` lifecycle validation (TDD passed) | `DONE` |
| **P2-04** | **3-Screen Dashboard** | Modern responsive SPA (Studio Feed, Reel Inspector with Video Player, Settings) (TDD passed) | `DONE` |
| **P2-05** | **Hybrid AI Router** | `AIRouter` with Ollama integration and Zero-AI resilient fallback (TDD passed) | `DONE` |
| **P3-01** | **Preset Validator** | Declarative JSON schema validator and safe loader for community presets (TDD passed) | `DONE` |
| **P3-02** | **Webhook Notifier** | Discord Embed and Telegram publish alerts with duration and chapters (TDD passed) | `DONE` |

---

## 📝 Activity & Development Log

- **2026-11-16**:
  - Completed comprehensive 4-round grilling session covering input scope, architecture, trimming, audio ducking, disk safety, hardware probes, and database strategy.
  - Authored `GLOSSARY.md` establishing standardized project domain language.
  - Recorded ADRs 0001 through 0007 in `docs/adr/`.
  - Authored 3 SVG diagram blueprints (`system-architecture.html`, `montage-pipeline.html`, `data-model.html`) verified against WCAG contrast and geometry checks.
  - Initialized Git repository and set remote to `https://github.com/posawatwichitsaro-bit/LazyCut.git`.
  - Created `PROGRESS.md` and initiated Phase 1 implementation.
