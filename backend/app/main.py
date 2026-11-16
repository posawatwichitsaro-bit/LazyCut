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

# Embedded Modern Studio Dashboard (Single Page App)
STUDIO_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LazyCut Studio</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg-dark: #090d16;
      --card-bg: #111827;
      --card-border: #1f2937;
      --accent: #f97316;
      --accent-hover: #ea580c;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --success: #10b981;
      --danger: #ef4444;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    body { font-family: var(--font); background: var(--bg-dark); color: var(--text-main); min-height: 100vh; padding: 1.5rem; }
    .container { max-width: 1200px; margin: 0 auto; }
    
    /* Header */
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; border-bottom: 1px solid var(--card-border); padding-bottom: 1rem; }
    .brand { display: flex; align-items: center; gap: 0.75rem; }
    .brand h1 { font-size: 1.6rem; color: var(--accent); font-weight: 700; }
    .header-badges { display: flex; gap: 0.75rem; }
    .chip { font-size: 0.75rem; padding: 0.3rem 0.6rem; border-radius: 9999px; font-weight: 600; border: 1px solid var(--card-border); background: var(--card-bg); color: var(--text-muted); }
    .chip-amf { border-color: #3b82f6; color: #60a5fa; }
    .chip-online { border-color: var(--success); color: var(--success); }

    /* Tab Nav */
    .nav-tabs { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
    .tab-btn { background: transparent; color: var(--text-muted); border: none; font-size: 1rem; font-weight: 600; padding: 0.6rem 1.2rem; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }
    .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
    .tab-btn:hover { color: var(--text-main); }

    /* Cards */
    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .card-title { font-size: 1.2rem; font-weight: 600; color: var(--text-main); }

    /* Buttons & Controls */
    .btn { background: var(--accent); color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 0.5rem; transition: background 0.2s; }
    .btn:hover { background: var(--accent-hover); }
    .btn-secondary { background: #374151; color: var(--text-main); }
    .btn-secondary:hover { background: #4b5563; }
    .btn-outline { background: transparent; border: 1px solid var(--card-border); color: var(--text-muted); }
    .btn-outline:hover { color: var(--text-main); border-color: var(--text-muted); }
    input[type="text"], select { background: #0b0f19; border: 1px solid var(--card-border); color: white; padding: 0.6rem 1rem; border-radius: 6px; font-size: 0.9rem; }
    input[type="text"]:focus, select:focus { outline: none; border-color: var(--accent); }

    /* Filter Pills */
    .filter-pills { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
    .pill { padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; cursor: pointer; background: #1f2937; color: var(--text-muted); border: 1px solid transparent; }
    .pill.active { background: var(--accent); color: white; font-weight: 600; }

    /* Tables */
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 0.75rem 1rem; border-bottom: 1px solid var(--card-border); }
    th { color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }
    .badge-kill { background: rgba(239, 68, 68, 0.15); border: 1px solid var(--danger); color: #f87171; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
    .badge-ok { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--success); color: #34d399; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }

    /* Floating Action Bar */
    .action-bar { position: sticky; bottom: 1.5rem; background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); }

    /* Video Player & Inspector */
    .video-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
    video { width: 100%; max-height: 480px; border-radius: 8px; background: black; border: 1px solid var(--card-border); }
    .pre-box { background: #0b0f19; border: 1px solid var(--card-border); padding: 1rem; border-radius: 6px; font-family: monospace; font-size: 0.85rem; color: #a7f3d0; white-space: pre-wrap; max-height: 240px; overflow-y: auto; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <span style="font-size: 2rem;">🎬</span>
        <div>
          <h1>LazyCut Studio</h1>
          <p style="font-size: 0.8rem; color: var(--text-muted);">Open-Source AI Video Automation Engine</p>
        </div>
      </div>
      <div class="header-badges">
        <span id="gpuBadge" class="chip chip-amf">GPU: Detecting...</span>
        <span id="gameGuardBadge" class="chip chip-online">Game Guard: Active</span>
      </div>
    </header>

    <!-- 3 Core Navigation Tabs -->
    <nav class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab('feed')">Studio Feed</button>
      <button class="tab-btn" onclick="switchTab('inspector')">Reel Inspector</button>
      <button class="tab-btn" onclick="switchTab('settings')">Settings</button>
    </nav>

    <!-- SCREEN 1: STUDIO FEED -->
    <section id="tab-feed">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Source Clips Library</span>
          <div style="display: flex; gap: 0.5rem;">
            <input type="text" id="manualImportInput" placeholder="Import path (e.g. D:\\clip.mp4)" style="width: 280px;" />
            <button class="btn btn-secondary" onclick="importManualClip()">Import</button>
            <button class="btn btn-outline" onclick="loadClips()">Refresh</button>
          </div>
        </div>

        <!-- Filter Pills -->
        <div class="filter-pills" id="filterPills" style="display: flex; align-items: center; gap: 0.5rem;">
          <button class="pill active" onclick="filterClips('all', this)">All Clips</button>
          <button class="pill" onclick="filterClips('kills', this)">🎯 Has Kills Only</button>
          <button class="pill" onclick="filterClips('duration', this)">⏱️ 5s–45s Only</button>
          <button class="pill" onclick="filterClips('verified', this)">Verified</button>
          <button class="btn btn-outline" style="font-size: 0.75rem; padding: 0.25rem 0.6rem; margin-left: auto;" onclick="rescanFolder()">🔄 Rescan Folder</button>
        </div>

        <table>
          <thead>
            <tr>
              <th style="width: 40px;"><input type="checkbox" id="selectAllCb" onclick="toggleSelectAll()" /></th>
              <th>File Name</th>
              <th>Duration</th>
              <th>Killfeed Status</th>
              <th>Verification</th>
            </tr>
          </thead>
          <tbody id="clipsTbody">
            <tr><td colspan="5" style="color: var(--text-muted); text-align: center; padding: 2rem;">Loading source clips...</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Action Generation Bar -->
      <div class="action-bar">
        <div style="display: flex; align-items: center; gap: 1rem;">
          <span id="selectionCounter" style="font-weight: 600;">0 clips selected</span>
          <button class="btn btn-outline" style="font-size: 0.8rem;" onclick="selectKillsOnly()">Select All with Kills</button>
        </div>
        <div style="display: flex; gap: 0.75rem; align-items: center;">
          <select id="vibeSelect">
            <option value="hype_montage">Hype Montage (Fast & Dynamic)</option>
            <option value="chill_memory">Chill Memory (Cinematic)</option>
            <option value="raw_clean">Raw Clean (Game Audio Only)</option>
          </select>
          <select id="formatSelect">
            <option value="16:9">16:9 Cinema Montage (Full Screen)</option>
            <option value="9:16">9:16 Vertical Short (TikTok/Reels)</option>
          </select>
          <button class="btn" onclick="startMontage()">⚡ Generate Montage</button>
        </div>
      </div>
    </section>

    <!-- SCREEN 2: REEL INSPECTOR -->
    <section id="tab-inspector" style="display: none;">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Reel Inspector & Player</span>
          <span id="jobStatusBadge" class="chip">No job selected</span>
        </div>

        <div class="video-grid">
          <div>
            <video id="videoPlayer" controls>
              <source id="videoSource" src="" type="video/mp4">
              Your browser does not support the video element.
            </video>
            <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
              <a id="downloadBtn" href="#" class="btn" target="_blank" style="display: none;">📥 Download Reel (.mp4)</a>
              <button class="btn btn-secondary" onclick="copyChapters()">📋 Copy Chapters</button>
            </div>
          </div>

          <div>
            <h3 style="font-size: 1rem; margin-bottom: 0.5rem; color: var(--accent);">AI / Zero-AI Metadata</h3>
            <p id="metaTitle" style="font-weight: 600; margin-bottom: 0.5rem;">No Reel rendered yet.</p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">YouTube / TikTok Chapters:</p>
            <div id="metaChapters" class="pre-box">Chapters will appear here after rendering.</div>
          </div>
        </div>
      </div>
    </section>

    <!-- SCREEN 3: SETTINGS -->
    <section id="tab-settings" style="display: none;">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Studio Settings</span>
        </div>
        <div style="max-width: 600px; display: flex; flex-direction: column; gap: 1.25rem;">
          <div>
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Folder Watcher Path</label>
            <div style="display: flex; gap: 0.5rem;">
              <input type="text" id="settingWatchPath" style="flex: 1;" placeholder="e.g. D:\\Outplayed\\Valorant" />
              <button class="btn" onclick="saveSettings()">Save & Watch</button>
            </div>
          </div>
          <div>
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Game Process Guard (Pause when playing)</label>
            <input type="checkbox" id="settingGameGuard" /> Enable auto-pause while VALORANT is running
          </div>
          <div>
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Hardware Video Acceleration</label>
            <select id="settingEncoder" style="width: 100%;">
              <option value="auto">Auto-Detect Best Hardware Encoder</option>
              <option value="h264_amf">AMD AMF Hardware Encoder</option>
              <option value="h264_nvenc">NVIDIA NVENC Hardware Encoder</option>
              <option value="h264_qsv">Intel QuickSync (QSV)</option>
              <option value="libx264">Software CPU (libx264)</option>
            </select>
          </div>
        </div>
      </div>
    </section>

  </div>

  <script>
    let currentFilter = 'all';
    let allClips = [];

    function switchTab(tabName) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('section').forEach(sec => sec.style.display = 'none');
      
      if (tabName === 'feed') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('tab-feed').style.display = 'block';
      } else if (tabName === 'inspector') {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('tab-inspector').style.display = 'block';
      } else if (tabName === 'settings') {
        document.querySelector('.tab-btn:nth-child(3)').classList.add('active');
        document.getElementById('tab-settings').style.display = 'block';
      }
    }

    async function loadStatus() {
      try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        document.getElementById('gpuBadge').innerText = `GPU: ${data.resolved_encoder}`;
        document.getElementById('settingWatchPath').value = data.watch_path || '';
        document.getElementById('settingGameGuard').checked = data.game_guard_enabled;
        document.getElementById('settingEncoder').value = data.preferred_encoder || 'auto';
      } catch (e) {
        console.error(e);
      }
    }

    async function saveSettings() {
      const path = document.getElementById('settingWatchPath').value;
      const guard = document.getElementById('settingGameGuard').checked;
      const enc = document.getElementById('settingEncoder').value;
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watch_path: path, game_guard_enabled: guard, preferred_encoder: enc })
      });
      alert('Settings saved!');
      loadStatus();
      loadClips();
    }

    async function loadClips() {
      let url = '/api/clips';
      if (currentFilter === 'kills') url += '?has_kills=true';
      if (currentFilter === 'duration') url += '?min_duration=5.0&max_duration=45.0';
      if (currentFilter === 'verified') url += '?is_verified=true';

      const res = await fetch(url);
      allClips = await res.json();
      renderClips();
    }

    function renderClips() {
      const tbody = document.getElementById('clipsTbody');
      if (allClips.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="color: var(--text-muted); text-align: center; padding: 2rem;">No source clips found matching criteria.</td></tr>';
        updateSelectionCount();
        return;
      }
      tbody.innerHTML = allClips.map(c => `
        <tr>
          <td><input type="checkbox" class="clip-cb" value="${c.id}" ${c.kill_count > 0 ? 'data-has-kill="1"' : ''} onchange="updateSelectionCount()" /></td>
          <td style="font-weight: 500;">${c.file_name}</td>
          <td>${c.duration.toFixed(1)}s</td>
          <td>${c.kill_count > 0 ? `<span class="badge-kill">🎯 ${c.kill_count} Kill${c.kill_count > 1 ? 's' : ''}</span>` : '<span style="color:var(--text-muted);">0 Kills</span>'}</td>
          <td>${c.is_verified ? '<span class="badge-ok">Verified</span>' : '<span style="color:var(--text-muted);">Unverified</span>'}</td>
        </tr>
      `).join('');
      updateSelectionCount();
    }

    function filterClips(filterType, el) {
      document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
      el.classList.add('active');
      currentFilter = filterType;
      loadClips();
    }

    function toggleSelectAll() {
      const master = document.getElementById('selectAllCb').checked;
      document.querySelectorAll('.clip-cb').forEach(cb => cb.checked = master);
      updateSelectionCount();
    }

    function selectKillsOnly() {
      document.querySelectorAll('.clip-cb').forEach(cb => {
        cb.checked = cb.dataset.hasKill === '1';
      });
      updateSelectionCount();
    }

    function updateSelectionCount() {
      const count = document.querySelectorAll('.clip-cb:checked').length;
      document.getElementById('selectionCounter').innerText = `${count} clip${count !== 1 ? 's' : ''} selected`;
    }

    async function rescanFolder() {
      try {
        const res = await fetch('/api/clips/scan', { method: 'POST' });
        const data = await res.json();
        alert(`Scanned library: Discovered ${data.total_clips} clips in folder!`);
        loadClips();
      } catch (e) {
        alert('Scan error: ' + e);
      }
    }

    async function importManualClip() {
      const path = document.getElementById('manualImportInput').value.trim();
      if (!path) return;
      try {
        const res = await fetch('/api/clips/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_path: path })
        });
        if (res.ok) {
          alert('Clip imported successfully!');
          document.getElementById('manualImportInput').value = '';
          loadClips();
        } else {
          alert('Could not import clip. Check file path.');
        }
      } catch (e) {
        alert('Import error: ' + e);
      }
    }

    async function startMontage() {
      const selected = Array.from(document.querySelectorAll('.clip-cb:checked')).map(cb => cb.value);
      if (selected.length === 0) {
        alert('Please select at least one clip!');
        return;
      }
      const vibe = document.getElementById('vibeSelect').value;
      const fmt = document.getElementById('formatSelect').value;

      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clip_ids: selected, vibe_id: vibe, output_format: fmt, target_duration: 60 })
      });
      const job = await res.json();
      switchTab('inspector');
      document.getElementById('jobStatusBadge').innerText = `Job ${job.id.substring(0,8)}: Processing...`;
      pollJob(job.id);
    }

    async function pollJob(jobId) {
      const interval = setInterval(async () => {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();
        document.getElementById('jobStatusBadge').innerText = `Job ${job.id.substring(0,8)}: ${job.status} (${(job.progress * 100).toFixed(0)}%)`;
        
        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
          clearInterval(interval);
          if (job.status === 'COMPLETED') {
            const expRes = await fetch(`/api/jobs/${jobId}/export`);
            const exp = await expRes.json();
            const filename = exp.output_path.split('\\\\').pop().split('/').pop();
            const reelUrl = `/exports/${filename}`;
            
            document.getElementById('videoPlayer').src = reelUrl;
            document.getElementById('downloadBtn').href = reelUrl;
            document.getElementById('downloadBtn').style.display = 'inline-flex';
            document.getElementById('metaTitle').innerText = exp.ai_title || 'Valorant Highlights';
            document.getElementById('metaChapters').innerText = exp.chapters || '';
          } else {
            alert('Job failed: ' + job.error_message);
          }
        }
      }, 1500);
    }

    function copyChapters() {
      const text = document.getElementById('metaChapters').innerText;
      navigator.clipboard.writeText(text);
      alert('Chapters copied to clipboard!');
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
        return HTMLResponse(content=STUDIO_DASHBOARD_HTML)
