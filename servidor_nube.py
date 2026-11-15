#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MG BARCELONA LIVE - SERVIDOR DE RADIO EN LA NUBE + HERRAMIENTA STUDIO WEB 24/7
==============================================================================
Todo en uno para ejecutar en un servidor gratuito en la nube (Render, HF Spaces,
Railway, Oracle Cloud, VPS o Docker):
  - GET  /stream         -> Emisión continua MP3 en directo 24/7 (AutoDJ + Directo)
  - GET  /panel          -> Herramienta completa MG Studio en la nube (web/móvil)
  - GET  /api/status     -> Estado en vivo, oyentes, pista actual, lista de pistas
  - POST /api/upload     -> Subir canciones MP3 o cuñas al servidor desde el navegador
  - POST /api/next       -> Saltar a la siguiente canción en el servidor
  - POST /api/play_track -> Reproducir una canción o cuña específica al instante
  - PUT/SOURCE /live     -> Entrada en directo desde MG Studio PC / BUTT / Icecast
"""

import os
import sys
import time
import json
import glob
import random
import shutil
import socket
import threading
import subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

BASE_DIR = Path(__file__).resolve().parent
MUSIC_DIR = BASE_DIR / "musica"
CUNAS_DIR = BASE_DIR / "cunas"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
CUNAS_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("PORT", "8080"))
ADMIN_PASS = os.environ.get("MG_ADMIN_PASS", "mg2026")
CUNA_INTERVAL = int(os.environ.get("MG_CUNA_INTERVAL", "3"))  # Cada 3 canciones suena 1 cuña


class CloudRadioEngine:
    def __init__(self):
        self.clients = set()
        self.clients_lock = threading.Lock()
        self.current_title = "MG Barcelona Live · Emisión 24/7"
        self.current_type = "autodj"  # 'autodj' o 'live'
        self.skip_requested = False
        self.forced_file = None
        self.tracks_since_cuna = 0
        self.live_active = False
        self.start_time = time.time()
        self.ffmpeg_bin = self._find_ffmpeg()

    def _find_ffmpeg(self):
        # 1. En PATH del servidor Linux/Docker o Windows
        p = shutil.which("ffmpeg")
        if p:
            return p
        # 2. Fallback en Windows local (CapCut u otros)
        local_candidates = glob.glob(os.path.expanduser(r"~\AppData\Local\CapCut\Apps\*\ffmpeg.exe"))
        if local_candidates:
            return local_candidates[-1]
        return "ffmpeg"

    def list_music(self):
        files = sorted(MUSIC_DIR.glob("*.mp3"))
        return [f.name for f in files]

    def list_cunas(self):
        files = sorted(CUNAS_DIR.glob("*.mp3"))
        return [f.name for f in files]

    def add_client(self, wfile):
        with self.clients_lock:
            self.clients.add(wfile)

    def remove_client(self, wfile):
        with self.clients_lock:
            self.clients.discard(wfile)

    def broadcast_chunk(self, chunk: bytes):
        if not chunk:
            return
        dead = []
        with self.clients_lock:
            for c in self.clients:
                try:
                    c.write(chunk)
                    c.flush()
                except Exception:
                    dead.append(c)
            for d in dead:
                self.clients.discard(d)

    def _pick_next_file(self):
        if self.forced_file and Path(self.forced_file).exists():
            f = Path(self.forced_file)
            self.forced_file = None
            return f

        music_files = sorted(MUSIC_DIR.glob("*.mp3"))
        cuna_files = sorted(CUNAS_DIR.glob("*.mp3"))

        if cuna_files and (self.tracks_since_cuna >= CUNA_INTERVAL or not music_files):
            self.tracks_since_cuna = 0
            chosen = random.choice(cuna_files)
            self.current_title = f"Cuña Oficial · {chosen.stem}"
            return chosen

        if music_files:
            self.tracks_since_cuna += 1
            chosen = random.choice(music_files)
            self.current_title = chosen.stem.replace("_", " ")
            return chosen

        return None

    def autodj_loop(self):
        while True:
            if self.live_active:
                time.sleep(0.5)
                continue

            next_file = self._pick_next_file()
            if not next_file:
                self.current_title = "MG Barcelona Live · Sube música en /panel"
                time.sleep(2.0)
                continue

            self.skip_requested = False
            cmd = [
                self.ffmpeg_bin,
                "-re",
                "-i", str(next_file),
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-ar", "44100",
                "-ac", "2",
                "-f", "mp3",
                "pipe:1"
            ]
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=4096
                )
                while proc.poll() is None:
                    if self.skip_requested or self.live_active:
                        proc.terminate()
                        break
                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        break
                    self.broadcast_chunk(chunk)
            except Exception:
                # Fallback: lectura directa de bytes MP3 si ffmpeg no tiene libmp3lame
                try:
                    with open(next_file, "rb") as fp:
                        while not self.skip_requested and not self.live_active:
                            chunk = fp.read(4096)
                            if not chunk:
                                break
                            self.broadcast_chunk(chunk)
                            time.sleep(0.24)  # ~128 kbps pacing
                except Exception:
                    time.sleep(1.0)


ENGINE = CloudRadioEngine()


PANEL_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MG Barcelona Live · Herramienta en el Servidor 24/7</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&display=swap');
  :root { --bg:#07050f; --card:#120d24; --neon:#b44fff; --cyan:#00f0ff; --pink:#ff2d78; --gold:#f5c842; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:#fff; font-family:'Inter',sans-serif; padding:1.5rem; }
  .wrap { max-width:1100px; margin:0 auto; }
  .header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:1rem; padding:1.4rem 1.8rem; background:var(--card); border:2px solid rgba(0,240,255,0.4); border-radius:20px; box-shadow:0 0 30px rgba(180,79,255,0.25); margin-bottom:1.5rem; }
  .title { font-family:'Bebas Neue',sans-serif; font-size:2.4rem; letter-spacing:0.06em; background:linear-gradient(90deg,#fff,var(--gold),var(--pink)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .badge { display:inline-flex; align-items:center; gap:0.5rem; padding:0.45rem 1rem; border-radius:999px; background:rgba(0,240,255,0.12); border:1px solid var(--cyan); color:var(--cyan); font-size:0.8rem; font-weight:700; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:1.4rem; }
  .card { background:var(--card); border:1px solid rgba(255,255,255,0.12); border-radius:18px; padding:1.5rem; }
  .card h2 { font-family:'Bebas Neue',sans-serif; font-size:1.7rem; color:var(--gold); letter-spacing:0.05em; margin-bottom:0.9rem; }
  .stat-row { display:flex; justify-content:space-between; padding:0.65rem 0; border-bottom:1px solid rgba(255,255,255,0.07); font-size:0.9rem; }
  .btn { display:inline-flex; align-items:center; justify-content:center; gap:0.4rem; padding:0.7rem 1.2rem; border-radius:999px; border:1px solid rgba(255,255,255,0.2); background:rgba(255,255,255,0.06); color:#fff; font-weight:600; font-size:0.85rem; cursor:pointer; transition:0.2s; text-decoration:none; }
  .btn:hover { border-color:var(--cyan); box-shadow:0 0 15px rgba(0,240,255,0.35); }
  .btn-primary { background:linear-gradient(135deg,var(--neon),var(--pink)); border:none; }
  .track-list { max-height:260px; overflow-y:auto; margin-top:0.8rem; border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:0.5rem; }
  .track-item { display:flex; align-items:center; justify-content:space-between; gap:0.5rem; padding:0.5rem 0.7rem; border-radius:8px; font-size:0.82rem; }
  .track-item:hover { background:rgba(255,255,255,0.06); }
  input[type="file"], input[type="password"] { width:100%; padding:0.65rem; border-radius:10px; border:1px solid rgba(255,255,255,0.2); background:#090614; color:#fff; margin-bottom:0.8rem; }
  audio { width:100%; margin-top:0.8rem; border-radius:999px; }
  .url-box { background:#090614; border:1px solid rgba(0,240,255,0.35); padding:0.75rem; border-radius:10px; font-family:monospace; font-size:0.82rem; color:var(--cyan); word-break:break-all; margin-top:0.6rem; }
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div>
      <div class="title">MG BARCELONA LIVE · SERVIDOR CLOUD 24/7</div>
      <p style="font-size:0.85rem;color:rgba(255,255,255,0.65);">Herramienta de control en el servidor · Emisión continua sin depender del PC</p>
    </div>
    <div class="badge" id="liveBadge">● EMITIENDO EN LA NUBE</div>
  </div>

  <div class="grid">
    <!-- Estado y Reproductor -->
    <div class="card">
      <h2>📡 Estado del Servidor en Vivo</h2>
      <div class="stat-row"><span>Sonando ahora:</span><strong id="nowPlaying" style="color:var(--cyan);">Cargando...</strong></div>
      <div class="stat-row"><span>Modo de emisión:</span><strong id="streamMode">AutoDJ 24/7</strong></div>
      <div class="stat-row"><span>Oyentes conectados:</span><strong id="listenersCount" style="color:var(--gold);">0</strong></div>
      <div style="margin-top:1rem;display:flex;gap:0.6rem;flex-wrap:wrap;">
        <button class="btn btn-primary" onclick="skipTrack()">⏭ Siguiente Canción</button>
        <a class="btn" href="/stream" target="_blank">🔗 Abrir Stream Directo</a>
      </div>
      <audio controls preload="none" src="/stream"></audio>
      <p style="font-size:0.78rem;color:rgba(255,255,255,0.5);margin-top:0.9rem;">URL fija de tu servidor para poner en la web:</p>
      <div class="url-box" id="streamUrlBox"></div>
    </div>

    <!-- Subir Música y Cuñas al Servidor -->
    <div class="card">
      <h2>☁️ Subir Música o Cuñas al Servidor</h2>
      <form id="uploadForm" onsubmit="uploadFiles(event)">
        <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Contraseña de administrador:</label>
        <input type="password" id="adminPass" value="mg2026" required>
        <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Tipo de audio:</label>
        <select id="uploadType" style="width:100%;padding:0.65rem;border-radius:10px;background:#090614;color:#fff;border:1px solid rgba(255,255,255,0.2);margin-bottom:0.8rem;">
          <option value="musica">🎵 Canción / Sesión MP3 (Carpeta Música)</option>
          <option value="cunas">🔊 Cuña de Radio (Carpeta Cuñas)</option>
        </select>
        <input type="file" id="audioFiles" accept=".mp3" multiple required>
        <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir al Servidor</button>
      </form>
      <p id="uploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
    </div>

    <!-- Biblioteca de Música en el Servidor -->
    <div class="card">
      <h2>🎵 Canciones en el Servidor (<span id="musicCount">0</span>)</h2>
      <div class="track-list" id="musicList"></div>
    </div>

    <!-- Biblioteca de Cuñas en el Servidor -->
    <div class="card">
      <h2>🔊 Cuñas Oficiales (<span id="cunasCount">0</span>)</h2>
      <div class="track-list" id="cunasList"></div>
    </div>
  </div>
</div>

<script>
document.getElementById('streamUrlBox').textContent = window.location.origin + '/stream';

async function refreshStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('nowPlaying').textContent = d.current_title || 'Sin pista';
    document.getElementById('streamMode').textContent = d.live_active ? '🔴 DIRECTO DESDE PC' : '🤖 AutoDJ Nube 24/7';
    document.getElementById('listenersCount').textContent = d.listeners;
    document.getElementById('musicCount').textContent = d.music.length;
    document.getElementById('cunasCount').textContent = d.cunas.length;

    const mEl = document.getElementById('musicList');
    mEl.innerHTML = d.music.length ? d.music.map(m =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">🎵 ${m}</span><button class="btn" style="padding:0.25rem 0.6rem;font-size:0.75rem;" onclick="playSpecific('musica', '${m.replace(/'/g,"\\'")}')">▶ Poner</button></div>`
    ).join('') : '<p style="font-size:0.8rem;color:rgba(255,255,255,0.4);padding:0.5rem;">Sube archivos MP3 para que suenen 24/7.</p>';

    const cEl = document.getElementById('cunasList');
    cEl.innerHTML = d.cunas.map(c =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">🔊 ${c}</span><button class="btn" style="padding:0.25rem 0.6rem;font-size:0.75rem;" onclick="playSpecific('cunas', '${c.replace(/'/g,"\\'")}')">🔊 Lanzar</button></div>`
    ).join('');
  } catch (e) {}
}

async function skipTrack() {
  await fetch('/api/next', { method: 'POST' });
  setTimeout(refreshStatus, 400);
}

async function playSpecific(folder, name) {
  await fetch('/api/play_track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder, name })
  });
  setTimeout(refreshStatus, 400);
}

async function uploadFiles(e) {
  e.preventDefault();
  const status = document.getElementById('uploadStatus');
  const files = document.getElementById('audioFiles').files;
  if (!files.length) return;
  const pass = document.getElementById('adminPass').value;
  const type = document.getElementById('uploadType').value;
  status.textContent = 'Subiendo archivos al servidor...';
  try {
    let subidos = 0;
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      status.textContent = `Subiendo (${i+1}/${files.length}): ${f.name}...`;
      const url = `/api/upload?type=${encodeURIComponent(type)}&name=${encodeURIComponent(f.name)}`;
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'X-Admin-Pass': pass },
        body: f
      });
      const res = await r.json();
      if (!res.ok) { status.textContent = res.message || 'Error'; return; }
      subidos++;
    }
    status.textContent = `✅ ${subidos} archivo(s) subidos al servidor correctamente`;
    document.getElementById('audioFiles').value = '';
    refreshStatus();
  } catch (err) {
    status.textContent = 'Error al subir archivo';
  }
}

refreshStatus();
setInterval(refreshStatus, 3000);
</script>
</body>
</html>
"""


class RadioHTTPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/panel"):
            body = PANEL_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/status":
            data = {
                "current_title": ENGINE.current_title,
                "live_active": ENGINE.live_active,
                "listeners": len(ENGINE.clients),
                "music": ENGINE.list_music(),
                "cunas": ENGINE.list_cunas(),
            }
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/stream":
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Pragma", "no-cache")
            self.send_header("Connection", "close")
            self.send_header("icy-name", "MG Barcelona Live")
            self.end_headers()
            ENGINE.add_client(self.wfile)
            try:
                while True:
                    time.sleep(1)
            except Exception:
                pass
            finally:
                ENGINE.remove_client(self.wfile)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/next":
            ENGINE.skip_requested = True
            raw = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/play_track":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            folder = CUNAS_DIR if body.get("folder") == "cunas" else MUSIC_DIR
            target = folder / Path(body.get("name", "")).name
            if target.exists():
                ENGINE.forced_file = str(target)
                ENGINE.current_title = target.stem.replace("_", " ")
                ENGINE.skip_requested = True
            raw = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/upload":
            qs = parse_qs(parsed.query)
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                raw = json.dumps({"ok": False, "message": "Contraseña incorrecta"}).encode("utf-8")
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return

            up_type = qs.get("type", ["musica"])[0]
            fname = Path(unquote(qs.get("name", ["pista.mp3"])[0])).name
            dest_dir = CUNAS_DIR if up_type == "cunas" else MUSIC_DIR
            length = int(self.headers.get("Content-Length", "0"))
            dest_path = dest_dir / fname
            remaining = length
            with open(dest_path, "wb") as out:
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)

            raw = json.dumps({"ok": True, "message": f"✅ {fname} subido correctamente"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    t = threading.Thread(target=ENGINE.autodj_loop, daemon=True)
    t.start()
    print(f"============================================================")
    print(f" MG BARCELONA LIVE - SERVIDOR EN LA NUBE INICIADO")
    print(f" Panel Herramienta : http://localhost:{PORT}/panel")
    print(f" Stream de Audio   : http://localhost:{PORT}/stream")
    print(f"============================================================")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), RadioHTTPHandler)
    server.serve_forever()
