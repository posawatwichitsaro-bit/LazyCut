# 🎬 LazyCut (Open-Source AI Video Automation Studio)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.10+-5C3EE8.svg)](https://opencv.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Hardware_Accelerated-007808.svg)](https://ffmpeg.org)

**LazyCut** is a local-first, semi-automated video editing studio designed to turn raw FPS gaming highlight clips (5s–45s from Outplayed, SteelSeries Moments, ShadowPlay, OBS) into polished long-form and 9:16 vertical shorts automatically.

Zero subscriptions. Zero cloud uploads required. 100% open-source.

---

## 🚀 Key Features

- **Local-First & Non-Destructive**: Reads Source Clips directly in-place without duplicating large video files. Original files are never modified or deleted.
- **Instant Killfeed & Action Detection (OpenCV)**: Uses lightweight computer vision to detect elimination banners and killfeeds in milliseconds on CPU, computing optimal Action Windows (`[-3.0s lead-in, +1.5s lead-out]`) and bridging multi-kills (`<4.0s`).
- **Deterministic 9:16 HUD Reframing**: Declarative JSON coordinate presets crop gameplay and stack in-game HUDs (killfeed, facecam) with blurred 1080x1920 background layers.
- **Smart Audio Ducking & Dynamic Endings**: Native FFmpeg `sidechaincompress` smoothly reduces BGM by `-14dB` during game action or voice comms, with 3 ending fade-out styles (Logarithmic, Exponential, and Low-pass sweep).
- **Game Process Guard**: Background monitor that automatically defers heavy rendering while games like `VALORANT.exe` are running to prevent in-game frame drops.
- **Hardware Acceleration Auto-Probe**: Automatically probes and leverages NVIDIA NVENC (`h264_nvenc`), AMD AMF (`h264_amf`), Intel QSV (`h264_qsv`), or CPU (`libx264`).
- **Optional AI Router with Zero-AI Fallback**: Generates catchy titles, tags, and timestamps via local (Ollama) or cloud models (BYOK), with automatic template fallbacks when offline.

---

## 🛠️ Architecture & Design Blueprints

LazyCut follows strict editorial design principles and rigorous Architecture Decision Records:
- **[System Architecture Blueprint](file:///d:/LazyCut/docs/diagrams/system-architecture.html)** (`docs/diagrams/system-architecture.html`)
- **[Montage Assembly Pipeline Blueprint](file:///d:/LazyCut/docs/diagrams/montage-pipeline.html)** (`docs/diagrams/montage-pipeline.html`)
- **[Data & Entity Model Blueprint](file:///d:/LazyCut/docs/diagrams/data-model.html)** (`docs/diagrams/data-model.html`)
- **[Domain Model (GLOSSARY.md)](file:///d:/LazyCut/GLOSSARY.md)**: Standardized domain terminology.
- **[Architecture Decision Records (docs/adr/)](file:///d:/LazyCut/docs/adr/)**: Architectural trade-offs and decisions.
- **[Progress Tracker (PROGRESS.md)](file:///d:/LazyCut/PROGRESS.md)**: Live task roadmap and changelog.

---

## ⚡ Quick Start (Windows One-Click)

1. Clone the repository:
   ```bash
   git clone https://github.com/posawatwichitsaro-bit/LazyCut.git
   cd LazyCut
   ```

2. Double-click **`start.bat`**:
   - Automatically sets up a Python virtual environment (`.venv`).
   - Installs all dependencies from `requirements.txt`.
   - Starts the FastAPI single-entrypoint backend on `http://localhost:8000`.
   - Automatically opens your default browser to the LazyCut Dashboard.

---

## 📁 Project Structure

```
LazyCut/
├── backend/                  # Python FastAPI Backend
│   └── app/
│       ├── api/              # REST Endpoints (Clips, Jobs, Presets, Settings)
│       ├── core/             # Config, SQLite DB, Hardware Probe, Disk Safety
│       ├── detection/        # OpenCV Killfeed & Skull Banner Detection Engine
│       ├── engine/           # FFmpeg Filter Graph & Montage Compositor
│       ├── models/           # SQLModel Entities (SourceClip, KillEvent, Jobs)
│       └── watcher/          # Watchdog Folder Monitor & Game Process Guard
├── presets/                  # Declarative JSON Game HUD Presets (e.g. valorant_1080p.json)
├── vibes/                    # Vibe Profiles (e.g. hype_montage.json, chill_memory.json)
├── music/                    # Royalty-Free / Custom BGM Audio (.mp3)
├── exports/                  # Rendered Output Reels (.mp4) and Chapters (.txt)
├── docs/
│   ├── adr/                  # Architecture Decision Records (0001–0007)
│   └── diagrams/             # Interactive SVG Architecture & Pipeline Blueprints
├── tests/                    # Automated Test Suite (pytest)
├── GLOSSARY.md               # Standard Domain Vocabulary
├── PROGRESS.md               # Project Progress & Roadmap Tracker
├── requirements.txt          # Python Dependencies
├── start.bat                 # Windows One-Click Bootstrap Launcher
└── README.md
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## Development context

See [LazyCut Context](Context/README.md) for the product brief, design decisions, Docker setup and development reports.
