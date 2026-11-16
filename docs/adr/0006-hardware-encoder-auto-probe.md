# Hardware Encoder Auto-Probe with Manual Override

Video encoding on consumer hardware varies significantly across NVIDIA, AMD, Intel, and CPU-only systems. We decided that LazyCut will automatically probe hardware encoders at startup (probing `h264_nvenc`, `h264_amf`, `h264_qsv`, and falling back to `libx264`), selecting the fastest supported encoder while allowing users to manually override the encoder in Settings. This delivers immediate high-performance 1080p60 rendering out-of-the-box without manual configuration.
