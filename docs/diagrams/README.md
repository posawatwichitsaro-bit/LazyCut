# LazyCut Architecture & Design Blueprints

This directory contains standalone, editorial SVG diagrams serving as the technical blueprints for LazyCut development. Each diagram is a self-contained HTML file rendering crisp vector graphics compliant with the project design system.

---

### 🗺️ Diagram Blueprints

1. **[System Architecture](file:///d:/LazyCut/docs/diagrams/system-architecture.html)** (`system-architecture.html`)
   - **Type**: Architecture / System Topology
   - **Scope**: Illustrates the Windows host boundary, single-process FastAPI core engine (serving static React UI + REST/WebSocket API), OpenCV detection engine, FFmpeg rendering pipeline, and local export boundary.

2. **[Montage Assembly Pipeline](file:///d:/LazyCut/docs/diagrams/montage-pipeline.html)** (`montage-pipeline.html`)
   - **Type**: Pipeline Flow / Unstructured Input → Structured Artifact
   - **Scope**: Maps the sequential transformation of 5s–45s Source Clips through OpenCV Killfeed detection, Action Window trimming (`[-3.0s, +1.5s]` with Kill-Chain Bridging), Duration Budget packing (max 15m), and FFmpeg composition (9:16 JSON cropping, audio ducking, and dynamic fade-out).

3. **[Data & Entity Model](file:///d:/LazyCut/docs/diagrams/data-model.html)** (`data-model.html`)
   - **Type**: ER / Logical Data Model
   - **Scope**: Defines the SQLite persistence schema (`source_clips`, `kill_events`, `montage_jobs`, `reel_exports`) and the external declarative JSON presets (`presets/*.json`, `vibes/*.json`).

---

*Generated via diagram-design with editorial styling (Instrument Serif, Geist, Geist Mono, WCAG contrast verified).*
