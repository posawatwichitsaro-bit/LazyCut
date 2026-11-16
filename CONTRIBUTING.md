# Contributing to LazyCut

Thank you for your interest in contributing to **LazyCut: Open-Source AI Video Automation Studio**!
LazyCut is built with a local-first, privacy-respecting philosophy designed to empower gaming content creators.

---

## 🛠️ Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/posawatwichitsaro-bit/LazyCut.git
   cd LazyCut
   ```

2. Initialize virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   ```

3. Run the automated test suite:
   ```bash
   pytest
   ```

---

## 🧪 Development Methodology: Test-Driven Development (TDD)

All new features and bug fixes follow the **Red ➔ Green ➔ Refactor** cycle:
1. Identify the public boundary/seam.
2. Write a failing test in `tests/` describing expected behavior.
3. Write the minimal code to make the test pass.
4. Ensure all existing tests pass (`pytest`).

---

## 🎮 Contributing New Game Presets

We welcome community presets for games like Apex Legends, Counter-Strike 2, Overwatch, and Call of Duty!
To add a new game preset:
1. Capture a standard 1080p (1920x1080) in-game screenshot showing the killfeed and elimination banner.
2. Define the pixel coordinates `(x, y, width, height)` in `presets/<game_name>_1080p.json`.
3. Verify your preset using the built-in validator:
   ```python
   from backend.app.core.preset_validator import validate_preset_dict
   ```
4. Read our detailed coordinate guide at [`docs/PRESET_GUIDE.md`](docs/PRESET_GUIDE.md).

---

## 📄 License
By contributing to LazyCut, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
