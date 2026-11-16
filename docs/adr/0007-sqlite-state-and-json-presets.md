# SQLite for Application State and JSON for Game Presets

LazyCut needs to persist clip scanning metadata, job histories, and application settings while also supporting custom game crop configurations. We decided to store application state, clip indexing, and job histories in an embedded SQLite database (`lazycut.db`), while storing Game Presets as discrete, human-editable JSON files in a dedicated `presets/` directory. This ensures ACID consistency and zero-server database management while enabling the open-source community to easily inspect, modify, and share game presets.
