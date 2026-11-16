import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings, BASE_DIR
from backend.app.core.database import init_db
from backend.app.watcher.folder_watcher import watcher_service
from backend.app.api.clips import router as clips_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.presets import router as presets_router
from backend.app.api.settings_router import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database & Watcher
    init_db()
    if settings.watch_path and Path(settings.watch_path).exists():
        watcher_service.start(settings.watch_path)
    yield
    # Shutdown: Stop Watcher
    watcher_service.stop()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(clips_router)
app.include_router(jobs_router)
app.include_router(presets_router)
app.include_router(settings_router)

# Mount exports directory for downloading rendered reels
app.mount("/exports", StaticFiles(directory=str(settings.exports_dir)), name="exports")

# Embedded Fallback UI for MVP
FALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LazyCut Studio (MVP)</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; }
    .card { background: #1e293b; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #334155; }
    h1 { color: #f97316; margin-top: 0; }
    h2 { color: #38bdf8; font-size: 1.2rem; }
    button { background: #ea580c; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; font-weight: 600; cursor: pointer; }
    button:hover { background: #c2410c; }
    input[type="text"] { background: #0f172a; border: 1px solid #475569; color: white; padding: 0.5rem; border-radius: 4px; width: 360px; }
    .badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-right: 0.5rem; }
    .badge-kill { background: #dc2626; color: white; }
    .badge-ok { background: #16a34a; color: white; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #334155; }
    th { color: #94a3b8; }
  </style>
</head>
<body>
  <h1>🎬 LazyCut Studio (MVP Phase 1)</h1>
  <p>Local-First AI Video Automation Engine for FPS Highlights.</p>

  <div class="card">
    <h2>📁 Watch Directory & System Status</h2>
    <div style="display: flex; gap: 1rem; align-items: center;">
      <input type="text" id="watchPathInput" placeholder="D:\\Outplayed\\Valorant" />
      <button onclick="saveWatchPath()">Save & Watch</button>
      <span id="statusSpan" style="color: #94a3b8;"></span>
    </div>
  </div>

  <div class="card">
    <h2>🎯 Detected Source Clips</h2>
    <div style="margin-bottom: 1rem;">
      <button onclick="loadClips()">Refresh Clips</button>
      <button style="background: #0284c7;" onclick="createMontage()">⚡ Generate 9:16 Reel (Selected)</button>
    </div>
    <table>
      <thead>
        <tr>
          <th><input type="checkbox" id="selectAll" onclick="toggleSelectAll()" /></th>
          <th>File Name</th>
          <th>Duration</th>
          <th>Kills Detected</th>
          <th>Verified</th>
        </tr>
      </thead>
      <tbody id="clipsTableBody">
        <tr><td colspan="5" style="color: #64748b;">No clips loaded yet. Enter watch folder or refresh.</td></tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>🚀 Recent Montage Jobs</h2>
    <div id="jobsList" style="color: #94a3b8;">No jobs run in this session.</div>
  </div>

  <script>
    async function loadStatus() {
      const res = await fetch('/api/settings');
      const data = await res.json();
      document.getElementById('watchPathInput').value = data.watch_path || '';
      document.getElementById('statusSpan').innerText = `GPU Encoder: ${data.resolved_encoder} | Game Active: ${data.is_game_running}`;
    }

    async function saveWatchPath() {
      const path = document.getElementById('watchPathInput').value;
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watch_path: path })
      });
      loadClips();
      loadStatus();
    }

    async function loadClips() {
      const res = await fetch('/api/clips');
      const clips = await res.json();
      const tbody = document.getElementById('clipsTableBody');
      if (clips.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="color: #64748b;">No clips found in folder.</td></tr>';
        return;
      }
      tbody.innerHTML = clips.map(c => `
        <tr>
          <td><input type="checkbox" class="clip-cb" value="${c.id}" ${c.kill_count > 0 ? 'checked' : ''} /></td>
          <td>${c.file_name}</td>
          <td>${c.duration.toFixed(1)}s</td>
          <td>${c.kill_count > 0 ? `<span class="badge badge-kill">🎯 ${c.kill_count} Kills</span>` : '<span style="color:#64748b;">0 Kills</span>'}</td>
          <td>${c.is_verified ? '<span class="badge badge-ok">Verified</span>' : 'Pending'}</td>
        </tr>
      `).join('');
    }

    function toggleSelectAll() {
      const master = document.getElementById('selectAll').checked;
      document.querySelectorAll('.clip-cb').forEach(cb => cb.checked = master);
    }

    async function createMontage() {
      const selected = Array.from(document.querySelectorAll('.clip-cb:checked')).map(cb => cb.value);
      if (selected.length === 0) {
        alert('Please select at least one clip!');
        return;
      }
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clip_ids: selected, target_duration: 60, output_format: "9:16" })
      });
      const job = await res.json();
      alert(`Job started! ID: ${job.id}`);
      pollJob(job.id);
    }

    async function pollJob(jobId) {
      const container = document.getElementById('jobsList');
      const interval = setInterval(async () => {
        const res = await fetch(`/api/jobs/${jobId}`);
        const data = await res.json();
        container.innerHTML = `Job <b>${data.id.substring(0,8)}</b>: Status = <span style="color:#ea580c; font-weight:bold;">${data.status}</span> (Progress: ${(data.progress * 100).toFixed(0)}%)`;
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          clearInterval(interval);
          if (data.status === 'COMPLETED') {
            const expRes = await fetch(`/api/jobs/${jobId}/export`);
            const expData = await expRes.json();
            const relPath = expData.output_path.split('\\\\').pop().split('/').pop();
            container.innerHTML += `<br/><a href="/exports/${relPath}" target="_blank" style="color:#38bdf8; font-weight:bold; display:inline-block; margin-top:0.5rem;">📥 Download Reel (.mp4)</a>`;
          }
        }
      }, 1500);
    }

    loadStatus();
    loadClips();
  </script>
</body>
</html>
"""

# Serve Static UI or Fallback
static_frontend = BASE_DIR / "frontend" / "out"
if static_frontend.exists() and (static_frontend / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(static_frontend), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def serve_fallback_ui():
        return HTMLResponse(content=FALLBACK_HTML)
