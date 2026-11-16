# Single-Process FastAPI Serving Static Web UI

LazyCut needs to run effortlessly on Windows gamer machines without requiring users to install and manage a Node.js runtime alongside Python. We decided that FastAPI will serve as the sole entrypoint, exposing REST/WebSocket APIs and serving the pre-compiled static frontend assets directly on a single port. This eliminates multi-server orchestration, cross-origin complexity, and Node.js dependencies for end users while preserving a modern React/Next.js developer experience.
