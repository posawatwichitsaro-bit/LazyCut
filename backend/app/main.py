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
      --bg-dark: #f3f2f7;
      --card-bg: #ffffff;
      --card-border: #dcd9e5;
      --accent: #663bce;
      --accent-hover: #5431b3;
      --text-main: #222033;
      --text-muted: #615e70;
      --success: #10b981;
      --danger: #ef4444;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    body { font-family: var(--font); background: var(--bg-dark); color: var(--text-main); min-height: 100vh; padding: 1.5rem; }
    .container { max-width: 1400px; margin: 0 auto; }
    
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
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
    .card-title { font-size: 1.2rem; font-weight: 600; color: var(--text-main); }

    /* Buttons & Controls */
    .btn { background: var(--accent); color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 0.5rem; transition: background 0.2s; font-size: 0.9rem; }
    .btn:hover { background: var(--accent-hover); }
    .btn-secondary { background: #374151; color: var(--text-main); }
    .btn-secondary:hover { background: #4b5563; }
    .btn-outline { background: transparent; border: 1px solid var(--card-border); color: var(--text-muted); }
    .btn-outline:hover { color: var(--text-main); border-color: var(--text-muted); }
    input[type="text"], select { background: #0b0f19; border: 1px solid var(--card-border); color: white; padding: 0.6rem 1rem; border-radius: 6px; font-size: 0.9rem; }
    input[type="text"]:focus, select:focus { outline: none; border-color: var(--accent); }

    /* Filter Pills */
    .filter-pills { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; align-items: center; }
    .pill { padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; cursor: pointer; background: #1f2937; color: var(--text-muted); border: 1px solid transparent; }
    .pill.active { background: var(--accent); color: white; font-weight: 600; }

    /* Clip Grid */
    .clip-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
    .clip-card { background: #0d1117; border: 2px solid var(--card-border); border-radius: 10px; overflow: hidden; cursor: pointer; transition: border-color 0.2s, transform 0.15s; position: relative; }
    .clip-card:hover { border-color: #374151; transform: translateY(-2px); }
    .clip-card.selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
    .clip-card .thumb { width: 100%; height: 150px; object-fit: cover; display: block; background: #000; }
    .clip-card .thumb-placeholder { width: 100%; height: 150px; display: flex; align-items: center; justify-content: center; background: #1a1a2e; color: var(--text-muted); font-size: 2rem; }
    .clip-card .info { padding: 0.75rem; }
    .clip-card .info .name { font-weight: 600; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 0.35rem; }
    .clip-card .info .meta { display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; color: var(--text-muted); }
    .clip-card .select-check { position: absolute; top: 8px; left: 8px; width: 22px; height: 22px; accent-color: var(--accent); cursor: pointer; }
    .badge-kill { background: rgba(239, 68, 68, 0.15); border: 1px solid var(--danger); color: #f87171; padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-ok { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--success); color: #34d399; padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-zero { color: var(--text-muted); font-size: 0.75rem; }

    /* Floating Action Bar */
    .action-bar { position: sticky; bottom: 1.5rem; background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); flex-wrap: wrap; gap: 0.75rem; z-index: 10; }

    /* Video Player & Inspector */
    .video-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
    video { width: 100%; max-height: 480px; border-radius: 8px; background: black; border: 1px solid var(--card-border); }
    .pre-box { background: #0b0f19; border: 1px solid var(--card-border); padding: 1rem; border-radius: 6px; font-family: monospace; font-size: 0.85rem; color: #a7f3d0; white-space: pre-wrap; max-height: 240px; overflow-y: auto; }

    /* Preview Modal */
    .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); z-index: 100; justify-content: center; align-items: center; }
    .modal-overlay.active { display: flex; }
    .modal-content { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.5rem; max-width: 720px; width: 90%; max-height: 90vh; overflow-y: auto; }
    .modal-content video { width: 100%; max-height: 380px; border-radius: 8px; margin-bottom: 1rem; }
    .modal-close { float: right; background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer; }
    .modal-close:hover { color: var(--text-main); }

    @media (max-width: 768px) {
      .clip-grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
      .video-grid { grid-template-columns: 1fr; }
      .action-bar { flex-direction: column; align-items: stretch; }
    }

    body { padding: 0; }
    .container { max-width: 1600px; padding: 0 clamp(16px, 4vw, 72px) 40px; }
    header { min-height: 74px; margin: 0; padding: 12px 0; }
    .brand h1 { font-size: 22px; letter-spacing: -.065em; color: var(--text-main); }
    .brand-mark { width: 32px; height: 32px; display: grid; place-items: center; background: #261e36; color: #c6ff80; border-radius: 9px; font-size: 26px; font-weight: 900; font-style: italic; }
    .header-badges { flex-wrap: wrap; justify-content: end; gap: 4px; }
    .chip-amf, .chip-online { background: #fff; color: #43404e; border-color: var(--card-border); }
    .nav-tabs { gap: 6px; margin: 16px 0 28px; flex-wrap: wrap; }
    .tab-btn { padding: 8px 14px; border: 0; font-size: 14px; border-radius: 7px; }
    .tab-btn.active { background: #e4dcf8; color: #512aa4; border: 0; }
    .workspace { display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, 320px); gap: 20px; align-items: start; }
    .card { border-radius: 16px; min-width: 0; }
    .card-title, .action-bar h2 { font-size: clamp(22px, 2.7vw, 34px); letter-spacing: -.055em; line-height: 1.15; }
    .card-header { align-items: center; gap: 14px; }
    .pill { background: #f2f0f6; color: #514d5c; }
    .clip-grid { grid-template-columns: repeat(auto-fill,minmax(min(220px,100%),1fr)); }
    .clip-card { background: #fff; }
    .selection-tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; border-top: 1px solid var(--card-border); padding-top: 14px; margin-top: 16px; }
    .empty-library { grid-column: 1/-1; min-height: 290px; display: grid; place-content: center; justify-items: center; padding: 24px; text-align: center; border-radius: 12px; background: radial-gradient(ellipse at 50% 42%,#e4daf6,transparent 60%),repeating-linear-gradient(135deg,#f3eff9 0 10px,#eeeaf5 10px 11px); }
    .slate { display:block; width:78px; height:50px; border-radius:6px; background:#312538; transform:rotate(-8deg); box-shadow:6px 7px 0 #c9b9e2; position:relative; margin: 10px 0 25px; }
    .slate::before { content:""; position:absolute; left:0; top:-8px; width:100%; height:13px; background:repeating-linear-gradient(125deg,#b6f885 0 11px,#312538 11px 22px); border-radius:3px; transform:rotate(-8deg); transform-origin:left bottom; }
    .slate::after { content:""; position:absolute; left:32px; top:19px; border-left:15px solid #e8dafa; border-top:9px solid transparent; border-bottom:9px solid transparent; }
    .empty-library strong { font-size: 21px; letter-spacing: -.04em; }
    .empty-library p { max-width: 38ch; color: var(--text-muted); margin: 6px 0 15px; }
    .action-bar { display: block; position: static; background: #231f30; color:#faf9ff; border: 0; border-radius: 16px; padding: 22px; box-shadow: none; }
    .action-bar h2 { font-size: 23px; margin-bottom: 20px; }
    .export-controls { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px 10px; }
    .export-controls label { font-size: 12px; color:#d3cddf; display:grid; align-content:start; gap:5px; }
    input[type=text], select, input[type=number] { background:#faf9fc; color:#252131; border:1px solid var(--card-border); border-radius:7px; padding:8px; max-width:100%; }
    .export-controls select,.export-controls input { width:100% !important; min-width:0; font-size:14px; background:#383343; color:#fff; border-color:#56505e; }
    .export-controls output,.export-controls button { grid-column:1/-1; }
    .export-controls output { border-top:1px solid #51495f; padding-top:14px; color:#d4cbe0; font-size:13px; }
    .export-controls button { justify-content:center; }
    #startFolderBtn { background:#bef488; color:#1e2b15; min-height:42px; }
    #startSelectionBtn { background:transparent; border:1px solid #696173; color:#eee; }
    .btn-secondary { background:#eeeaf4; }
    .btn-secondary:hover { background:#dfd8e9; }
    .video-grid { grid-template-columns:minmax(0,2fr) minmax(220px,1fr); }
    .video-grid > div { min-width:0; }
    .pre-box { background:#f3f1f7; color:#393342; margin-bottom:16px; }
    .modal-close { color:var(--text-main); }
    :focus-visible { outline:3px solid #a485fa !important; outline-offset:2px; }
    @media(max-width:850px) { .workspace,.video-grid { grid-template-columns:minmax(0,1fr); } .empty-library {min-height:190px;} }
    @media(max-width:520px) { header {align-items:start;} .card,.action-bar {padding:16px;} .chip {font-size:10px;} .nav-tabs {gap:0;} }
    .orientation {grid-column:1/-1; display:grid; grid-template-columns:1fr 1fr; gap:8px; border:0; min-width:0}
    .orientation legend {color:#dbd7e3;font-size:13px;margin-bottom:7px}
    .orientation label {position:relative;cursor:pointer}
    .orientation input {position:absolute;opacity:0;width:1px!important;height:1px}
    .orientation span {display:grid;grid-template-columns:1fr auto;align-items:center;gap:4px;padding:13px 10px;border-radius:9px;border:1px solid #736b81;font-size:14px}
    .orientation i {grid-column:1/-1;border:2px solid currentColor;border-radius:3px;margin-bottom:6px}
    .wide-frame {width:25px;height:15px}.tall-frame {width:15px;height:25px}
    .orientation span {grid-template-rows:28px auto}
    .orientation small {font-size:11px}.orientation input:checked+span {background:#e9defd;color:#322447;border-color:#bda0ea}
    .orientation input:focus-visible+span {outline:3px solid #bef488;outline-offset:2px}
    .selection-tools[hidden] {display:none}
    #startSelectionBtn {margin-left:auto;background:#5833aa;color:white;border:0}
    button:disabled,#startFolderBtn:disabled {background:#453f50;color:#d5cedf;cursor:not-allowed;opacity:.72}
    #queueHint {grid-column:1/-1;color:#dfd8e8;font-size:12px;text-align:center}
    .btn,.pill {min-height:36px}.btn:not(:disabled):active {transform:translateY(1px)}
    #notice:not(:empty) {position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:120;background:#282132;color:white;padding:12px 18px;border-radius:10px;box-shadow:0 5px 24px #22113633;max-width:90vw}
  </style>
</head>
<body>
  <div class="container">
    <div id="notice" role="status" aria-live="polite"></div>
    <header>
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">L</span>
        <h1>LazyCut Studio</h1>
      </div>
      <div class="header-badges">
        <span id="gpuBadge" class="chip chip-amf">GPU: Detecting...</span>
        <span id="gameGuardBadge" class="chip">Game Guard: …</span>
      </div>
    </header>

    <!-- 3 Core Navigation Tabs -->
    <nav class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab('feed')">Studio Feed</button>
      <button class="tab-btn" onclick="switchTab('inspector')">Reel Inspector</button>
      <button class="tab-btn" onclick="switchTab('settings')">Settings</button>
    </nav>

    <!-- SCREEN 1: CLIP PICKER GRID -->
    <section id="tab-feed">
      <div class="workspace">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Clip library</span>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <button class="btn btn-outline" style="font-size: 0.8rem;" onclick="rescanFolder()">Scan &amp; analyze folder</button>
            <button class="btn btn-outline" style="font-size: 0.8rem;" onclick="loadClips()">Refresh list</button>
          </div>
        </div>

        <!-- Filter Pills -->
        <div class="filter-pills" id="filterPills">
          <button class="pill active" onclick="filterClips('all', this)">All Clips</button>
          <button class="pill" onclick="filterClips('kills', this)">Has Kills</button>
          <button class="pill" onclick="filterClips('verified', this)">Verified</button>
          <span id="clipCountLabel" style="margin-left: auto; font-size: 0.8rem; color: var(--text-muted);">0 clips</span>
        </div>

        <!-- Clip Grid -->
        <div class="clip-grid" id="clipGrid">
          <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">Loading clips...</div>
        </div>
        <div class="selection-tools">
          <span id="selectionCounter" style="font-weight: 600;">0 clips selected</span>
          <button class="btn btn-outline" style="font-size: 0.8rem;" onclick="selectAll()">Select All</button>
          <button class="btn btn-outline" style="font-size: 0.8rem;" onclick="selectKillsOnly()">Select Kills Only</button>
          <button class="btn btn-outline" style="font-size: 0.8rem;" onclick="deselectAll()">Clear selection</button>
          <button class="btn" id="startSelectionBtn" disabled onclick="startMontage()">Create from selected clips</button>
        </div>
      </div>
      <aside class="action-bar">
        <h2>Create highlights</h2>
        <div class="export-controls">
          <fieldset class="orientation"><legend>Video layout</legend>
            <label><input type="radio" name="layout" value="16:9" checked><span><i class="wide-frame"></i>Landscape<small>16:9</small></span></label>
            <label><input type="radio" name="layout" value="9:16"><span><i class="tall-frame"></i>Portrait<small>9:16</small></span></label>
          </fieldset>
          <label>Style<select id="vibeSelect" aria-label="Editing style">
            <option value="hype_montage">Hype Montage</option>
            <option value="chill_memory">Chill Memory</option>
            <option value="raw_clean">Raw Clean</option>
          </select>
          </label><label>Length <select id="durationProfile" onchange="updateOutputLimit()">
            <option value="short">Short</option>
            <option value="long">Long</option>
          </select></label>
          <label>Max seconds per Reel <input id="montageDuration" type="number" min="1" max="180" oninput="updateOutputLimit()" step="1" value="120" required style="width: 4.5rem;"></label>
          <label>Max Reels <input id="maxReels" type="number" min="1" value="3"
            required oninput="updateOutputLimit()" style="width: 4rem;"></label>
          <output id="maxTotalDuration" aria-live="polite">Up to 6 min 0 sec total</output>

          <button class="btn" id="startFolderBtn" disabled onclick="startMontage(true)">Create folder highlights</button>
          <small id="queueHint">Checking the recording folder…</small>
        </div>
      </aside>
      </div>
    </section>

    <!-- SCREEN 2: REEL INSPECTOR -->
    <section id="tab-inspector" style="display: none;">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Reel Inspector & Player</span>
          <span id="jobStatusBadge" class="chip">No job selected</span>
        </div>

        <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem;">
          <label>Reel <select id="reelSelect" onchange="showReel()" disabled></select></label>
          <button class="btn btn-outline" onclick="showExportHistory()">Export history</button>
        </div>
        <div class="video-grid">
          <div>
            <video id="videoPlayer" controls>
              Your browser does not support the video element.
            </video>
            <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
              <a id="downloadBtn" href="#" class="btn" target="_blank" style="display: none;">Download Reel (.mp4)</a>
              <button id="copyBtn" class="btn btn-secondary" disabled onclick="copyChapters()">Copy Chapters</button>
            </div>
          </div>

          <div>
            <h3 style="font-size: 1rem; margin-bottom: 0.5rem; color: var(--accent);">Reel details</h3>
            <p id="metaTitle" style="font-weight: 600; margin-bottom: 0.5rem;">No Reel rendered yet.</p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">YouTube / TikTok Chapters:</p>
            <div id="metaChapters" class="pre-box">Chapters will appear here after rendering.</div>
            <label for="reelRating">Rate this Reel</label>
            <select id="reelRating" onchange="saveReelRating()" disabled>
              <option value="">Choose rating</option>
              <option>ดีมาก</option><option>ดี</option><option>แย่</option><option>แย่มาก</option>
            </select>
            <p id="ratingCounts" class="muted" aria-live="polite"></p>
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

    <!-- Preview Modal -->
    <div class="modal-overlay" id="previewModal" onclick="closePreview(event)">
      <div class="modal-content" onclick="event.stopPropagation()">
        <button class="modal-close" onclick="closePreview()">&times;</button>
        <video id="previewPlayer" controls></video>
        <h3 id="previewName" style="margin-bottom: 0.5rem;"></h3>
        <div id="previewMeta" style="font-size: 0.85rem; color: var(--text-muted);"></div>
        <fieldset style="margin-top: 0.75rem; padding: 0.5rem;">
          <legend>Montage timing for all clips</legend>
          <label>Before (s) <input id="highlightPre" type="number" min="0" max="60" step="0.5" value="4.5" style="width: 4.5rem;"></label>
          <label>After (s) <input id="highlightPost" type="number" min="0.5" max="60" step="0.5" value="2.5" style="width: 4.5rem;"></label>
        </fieldset>
        <div id="previewAnalysis" style="margin-top: 1rem; max-height: 12rem; overflow-y: auto;"></div>
      </div>
    </div>
  </div>

  <script>
    let currentFilter = 'all';
    let allClips = [];
    let selectedIds = new Set();
    const eventSelections = new Map();
    let previewRequest = 0;
    let previewEnd = null;
    const previewPlayer = document.getElementById('previewPlayer');
    previewPlayer.addEventListener('timeupdate', () => {
      if (previewEnd !== null && previewPlayer.currentTime >= previewEnd) {
        previewPlayer.pause();
        previewEnd = null;
      }
    });

    function readHighlightTiming() {
      const pre = document.getElementById('highlightPre');
      const post = document.getElementById('highlightPost');
      if (!pre.reportValidity() || !post.reportValidity() || !pre.value || !post.value) return null;
      return { pre: Number(pre.value), post: Number(post.value) };
    }

    function openFolderSettings() {
      switchTab('settings');
      document.getElementById('settingWatchPath').focus();
    }

    let noticeTimer;
    function showNotice(message) {
      const notice = document.getElementById('notice');
      notice.textContent = message;
      clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => { notice.textContent = ''; }, 7000);
    }

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
        const guardBadge = document.getElementById('gameGuardBadge');
        guardBadge.textContent = data.game_guard_enabled ? 'Game Guard: Enabled' : 'Game Guard: Off';
        guardBadge.classList.toggle('chip-online', data.game_guard_enabled);
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
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watch_path: path, game_guard_enabled: guard, preferred_encoder: enc })
      });
      if (!res.ok) return showNotice('Could not save settings. Please try again.');
      showNotice('Settings saved.');
      loadStatus();
      loadClips();
    }

    let libraryHasClips = false;
    async function loadClips() {
      const res = await fetch('/api/clips');
      if (!res.ok) return showNotice('Could not refresh recordings. Try Refresh list.');
      const clips = await res.json();
      libraryHasClips = clips.length > 0;
      allClips = clips.filter(clip => currentFilter === 'all' ||
        (currentFilter === 'kills' ? clip.kill_count > 0 : clip.is_verified));
      document.getElementById('clipCountLabel').innerText = `${allClips.length} clips`;
      renderClipGrid();
    }

    function renderClipGrid() {
      const grid = document.getElementById('clipGrid');
      if (allClips.length === 0) {
        grid.innerHTML = !libraryHasClips
          ? `<div class="empty-library"><span class="slate" aria-hidden="true"></span><strong>No recordings yet</strong><p>Save a gameplay recording in your watched folder. It will appear here when ready.</p><button class="btn" onclick="openFolderSettings()">Set recording folder</button></div>`
          : '<div class="empty-library"><strong>No matching clips</strong><p>Choose All Clips to see the full library.</p></div>';
        updateSelectionCount();
        return;
      }
      grid.innerHTML = allClips.map(c => {
        const isSelected = selectedIds.has(c.id);
        const killBadge = c.kill_count > 0
          ? `<span class="badge-kill">${c.kill_count} Kill${c.kill_count > 1 ? 's' : ''}</span>`
          : '<span class="badge-zero">0 Kills</span>';
        return `
          <div class="clip-card ${isSelected ? 'selected' : ''}" data-id="${c.id}" onclick="toggleClipSelect('${c.id}')">
            <input type="checkbox" class="select-check" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleClipSelect('${c.id}')" />
            <img class="thumb" src="/api/clips/${c.id}/thumbnail" alt="${c.file_name}" loading="lazy" onerror="this.outerHTML='<div class=\\'thumb-placeholder\\'>🎮</div>'" />
            <div class="info">
              <div class="name" title="${c.file_name}">${c.file_name}</div>
              <div class="meta">
                <span>${c.duration.toFixed(1)}s</span>
                ${killBadge}
                <button class="btn btn-outline" style="font-size: 0.7rem; padding: 0.15rem 0.4rem;" onclick="event.stopPropagation(); openPreview('${c.id}')">▶ Preview</button>
              </div>
            </div>
          </div>`;
      }).join('');
      updateSelectionCount();
    }

    function toggleClipSelect(id) {
      if (selectedIds.has(id)) {
        selectedIds.delete(id);
      } else {
        selectedIds.add(id);
      }
      renderClipGrid();
    }

    function selectAll() {
      allClips.forEach(c => selectedIds.add(c.id));
      renderClipGrid();
    }

    function selectKillsOnly() {
      selectedIds.clear();
      allClips.filter(c => c.kill_count > 0).forEach(c => selectedIds.add(c.id));
      renderClipGrid();
    }

    function deselectAll() {
      selectedIds.clear();
      renderClipGrid();
    }

    function updateSelectionCount() {
      const count = selectedIds.size;
      const manual = document.getElementById('startSelectionBtn');
      manual.disabled = jobRunning || count === 0;
      manual.textContent = count ? `Create from ${count} selected` : 'Create from selected clips';
      const empty = !libraryHasClips;
      document.querySelector('.selection-tools').hidden = empty && count === 0;
      document.getElementById('startFolderBtn').disabled = jobRunning || empty;
      document.getElementById('queueHint').textContent = empty
        ? 'Add a recording to your folder to start.'
        : 'Uses ready recordings in your folder. No selection needed.';
      document.getElementById('selectionCounter').innerText = `${count} clip${count !== 1 ? 's' : ''} selected`;
    }

    function filterClips(filterType, el) {
      document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
      el.classList.add('active');
      currentFilter = filterType;
      loadClips();
    }

    async function openPreview(clipId) {
      const clip = allClips.find(c => c.id === clipId);
      if (!clip) return;
      const modal = document.getElementById('previewModal');
      const player = document.getElementById('previewPlayer');
      const request = ++previewRequest;
      previewEnd = null;
      document.getElementById('previewName').innerText = clip.file_name;
      document.getElementById('previewMeta').innerText = `Duration: ${clip.duration.toFixed(1)}s | Kills: ${clip.kill_count} | ${clip.is_verified ? 'Verified' : 'Unverified'}`;
      
      // Load analysis
      document.getElementById('previewAnalysis').innerHTML = '<p style="color: var(--text-muted);">Analyzing highlights...</p>';
      
      // Set real video stream source for preview
      player.poster = `/api/clips/${clipId}/thumbnail`;
      player.src = `/api/clips/${clipId}/stream`;
      player.load();
      
      modal.classList.add('active');

      const panel = document.getElementById('previewAnalysis');
      try {
        const res = await fetch(`/api/clips/${clipId}/analyze`);
        const data = await res.json();
        if (request !== previewRequest) return;
        if (!res.ok) throw new Error(data.detail || 'Analysis failed.');
        document.getElementById('previewMeta').textContent =
          `Duration: ${data.duration.toFixed(1)}s | Kills: ${data.moments.length}`;
        panel.replaceChildren();
        const previous = eventSelections.get(clipId);
        if (previous && previous.revision !== data.revision) eventSelections.delete(clipId);

        if (!data.moments.length) {
          panel.textContent = 'No combat highlights detected in this clip.';
        } else {
          const selected = new Set(eventSelections.get(clipId)?.event_indices ?? data.moments.map((_, index) => index));
          const caption = document.createElement('p');
          caption.textContent = 'Include events in montage';
          panel.append(caption);
          data.moments.forEach((moment, index) => {
            const row = document.createElement('div');
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = selected.has(index);
            checkbox.addEventListener('change', () => {
              if (checkbox.checked) selected.add(index);
              else selected.delete(index);
              if (selected.size === data.moments.length) eventSelections.delete(clipId);
              else eventSelections.set(clipId, { revision: data.revision, event_indices: [...selected] });
            });
            label.append(checkbox, ` ${moment.timestamp.toFixed(2)}s · ${moment.is_headshot ? 'Headshot kill' : 'Kill'} `);
            const jump = document.createElement('button');
            jump.className = 'btn btn-outline';
            jump.textContent = 'Preview event';
            jump.addEventListener('click', () => {
              const timing = readHighlightTiming();
              if (!timing) return;
              player.currentTime = Math.max(0, moment.timestamp - timing.pre);
              previewEnd = Math.min(data.duration, moment.timestamp + timing.post);
              player.play().catch(() => { previewEnd = null; });
            });
            row.append(label, jump);
            panel.append(row);
          });
        }
        loadClips();
      } catch (e) {
        if (request === previewRequest) panel.textContent = e.message;
      }
    }

    function closePreview(e) {
      if (e && e.target !== document.getElementById('previewModal') && !e.target.classList.contains('modal-close')) return;
      const player = document.getElementById('previewPlayer');
      previewRequest++;
      previewEnd = null;
      player.pause();
      player.removeAttribute('src');
      document.getElementById('previewModal').classList.remove('active');
    }

    async function rescanFolder() {
      try {
        const res = await fetch('/api/clips/scan', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Could not scan folder');
        showNotice(`Scanned: ${data.total_clips} clips in library!`);
        loadClips();
      } catch (e) {
        showNotice('Scan error: ' + e);
      }
    }

    let displayedReels = [];
    let reelRatings = {};
    let jobRunning = false;

    function updateOutputLimit() {
      const duration = document.getElementById('montageDuration');
      duration.max = document.getElementById('durationProfile').value === 'short' ? 180 : 900;
      const count = document.getElementById('maxReels');
      const total = duration.valueAsNumber * count.valueAsNumber;
      document.getElementById('maxTotalDuration').textContent = duration.validity.valid && count.validity.valid
        ? `Up to ${Math.floor(total / 60)} min ${total % 60} sec total` : '';
    }

    async function startMontage(folderQueue = false) {
      if (jobRunning) return;
      const selected = folderQueue ? [] : Array.from(selectedIds);
      if (!folderQueue && selected.length === 0) {
        showNotice('Please select at least one clip!');
        return;
      }
      const timing = readHighlightTiming();
      if (!timing) return;
      const duration = document.getElementById('montageDuration');
      if (!duration.reportValidity()) return;
      const maximum = document.getElementById('maxReels');
      if (folderQueue && !maximum.reportValidity()) return;
      const selections = Object.fromEntries(selected.filter(id => eventSelections.has(id)).map(id => [id, eventSelections.get(id)]));
      const vibe = document.getElementById('vibeSelect').value;
      const fmt = document.querySelector('input[name=layout]:checked').value;

      jobRunning = true;
      const buttons = [document.getElementById('startSelectionBtn'), document.getElementById('startFolderBtn')];
      buttons.forEach(button => button.disabled = true);
      try {
        const res = await fetch('/api/jobs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            folder_queue: folderQueue, clip_ids: selected, vibe_id: vibe, output_format: fmt,
            target_duration: duration.valueAsNumber, timing, selections,
            max_reels: folderQueue ? maximum.valueAsNumber : 1,
            duration_profile: document.getElementById('durationProfile').value
          })
        });
        const job = await res.json();
        if (!res.ok) throw new Error(typeof job.detail === 'string' ? job.detail : 'Could not create montage.');
        switchTab('inspector');
        document.getElementById('jobStatusBadge').textContent = 'Starting export…';
        setDisplayedReels([]);
        await pollJob(job.id);
      } catch (error) {
        showNotice(error.message);
      } finally {
        jobRunning = false;
        updateSelectionCount();
      }
    }

    async function pollJob(jobId) {
      const badge = document.getElementById('jobStatusBadge');
      while (true) {
        const response = await fetch(`/api/jobs/${jobId}`);
        if (!response.ok) throw new Error('Could not read job status.');
        const job = await response.json();
        badge.textContent = `${job.status} (${Math.round(job.progress * 100)}%)`;
        if (job.status === 'NO_HIGHLIGHTS') {
          badge.textContent = 'No eligible player kills remain for this job.';
          return;
        }
        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
          const results = await fetch(`/api/jobs/${jobId}/exports`);
          if (!results.ok) throw new Error('Could not load exported Reels.');
          const exports = await results.json();
          setDisplayedReels(exports);
          badge.textContent = job.status === 'FAILED'
            ? `Failed after ${exports.length} export(s) — ${job.error_message}`
            : `${exports.length} Reel(s) exported`;
          await refreshRatings();
          return;
        }
        await new Promise(resolve => setTimeout(resolve, 1500));
      }
    }

    function setDisplayedReels(exports) {
      displayedReels = exports;
      const picker = document.getElementById('reelSelect');
      picker.replaceChildren(...exports.map((reel, index) =>
        new Option(`Reel ${index + 1} · ${reel.filename}`, reel.id)));
      picker.disabled = exports.length === 0;
      showReel();
    }

    function currentReel() {
      const id = document.getElementById('reelSelect').value;
      return displayedReels.find(reel => reel.id === id);
    }

    function showReel() {
      const reel = currentReel();
      const player = document.getElementById('videoPlayer');
      const download = document.getElementById('downloadBtn');
      if (reel) {
        const url = `/exports/${encodeURIComponent(reel.filename)}`;
        player.src = url;
        download.href = url;
      } else {
        player.removeAttribute('src');
        player.load();
        download.removeAttribute('href');
      }
      document.getElementById('copyBtn').disabled = !reel?.chapters;
      download.style.display = reel ? 'inline-flex' : 'none';
      document.getElementById('metaTitle').textContent = reel?.ai_title || '';
      document.getElementById('metaChapters').textContent = reel?.chapters || '';
      syncRating();
    }

    function syncRating() {
      const reel = currentReel();
      const control = document.getElementById('reelRating');
      control.disabled = !reel;
      control.value = reelRatings[reel?.id] || '';
    }

    function showRatingCounts(counts) {
      document.getElementById('ratingCounts').textContent = Object.entries(counts)
        .map(([label, count]) => `${label} ${count}`).join(' · ');
    }

    async function refreshRatings(showHistory = false) {
      const res = await fetch('/api/jobs/reels/history');
      if (!res.ok) throw new Error('Could not load export history.');
      const history = await res.json();
      reelRatings = history.ratings;
      showRatingCounts(history.counts);
      if (showHistory) setDisplayedReels(history.exports);
      else syncRating();
    }

    async function showExportHistory() {
      try {
        await refreshRatings(true);
        if (!jobRunning) document.getElementById('jobStatusBadge').textContent = 'Export history';
      } catch (error) {
        showNotice(error.message);
      }
    }

    async function saveReelRating() {
      const reel = currentReel();
      const control = document.getElementById('reelRating');
      if (!reel || !control.value) {
        syncRating();
        return;
      }
      const rating = control.value;
      control.disabled = true;
      try {
        const response = await fetch(`/api/jobs/reels/${reel.id}/rating`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rating })
        });
        if (!response.ok) throw new Error('Could not save Reel rating.');
        const result = await response.json();
        reelRatings[reel.id] = result.rating;
        showRatingCounts(result.counts);
      } catch (error) {
        showNotice(error.message);
      } finally {
        syncRating();
      }
    }

    function copyChapters() {
      const text = document.getElementById('metaChapters').innerText;
      navigator.clipboard.writeText(text);
      showNotice('Chapters copied to clipboard!');
    }

    loadStatus();
    loadClips();
    setInterval(() => {
      if (!document.hidden && !jobRunning && !libraryHasClips &&
          document.getElementById('tab-feed').style.display !== 'none') {
        loadClips().catch(() => {});
      }
    }, 5000);
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
