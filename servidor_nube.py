#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MG BARCELONA LIVE - SERVIDOR DE RADIO EN LA NUBE + HERRAMIENTA TOTAL WEB 24/7
=============================================================================
Desde este único panel en el servidor (/panel) controlas y sirves TODO:
  1. 🎵 LA RADIO, MÚSICA Y CUÑAS 24/7 (AutoDJ sin necesitar Virtual DJ)
  2. 🎨 LAS 16 PLANTILLAS DE LA WEB EN VIVO
  3. 🎬 LOS VÍDEOS MUSICALES Y LA PUBLICIDAD EN VÍDEO
  4. 📸 LAS FOTOGRAFÍAS DE MOISÉS GALLARDO (Galería visual y subida de fotos)
"""

import os
import sys
import time
import json
import glob
import base64
import random
import shutil
import socket
import threading
import subprocess
import mimetypes
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
WEB_DIR = ROOT_DIR / "MG Barcelona Live"

MUSIC_DIR = BASE_DIR / "musica"
CUNAS_DIR = BASE_DIR / "cunas"
VIDEOS_DIR = BASE_DIR / "videos"
PUBLICIDAD_DIR = BASE_DIR / "publicidad"
FOTOS_DIR = BASE_DIR / "eventos_fotos"

for _d in (MUSIC_DIR, CUNAS_DIR, VIDEOS_DIR, PUBLICIDAD_DIR, FOTOS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("PORT", "8080"))
ADMIN_PASS = os.environ.get("MG_ADMIN_PASS", "mg2026")
CUNA_INTERVAL = int(os.environ.get("MG_CUNA_INTERVAL", "3"))
GITHUB_REPO = "mgbarcelonalive/mgbarcelonalive.github.io"

PLANTILLAS_DISPONIBLES = [
    ("principal", "🏆 Principal Club"),
    ("disco", "🪩 Disco Fever"),
    ("neon", "⚡ Neón Cyber"),
    ("lgtb", "🏳️‍🌈 Pride LGTB"),
    ("dragrace", "👑 Drag Race"),
    ("cyberpunk", "🤖 Cyberpunk"),
    ("sunset", "🌅 Sunset Beach"),
    ("moderna", "✨ Moderna"),
    ("clasica", "🏛️ Clásica"),
    ("cine", "🎬 Cine"),
    ("azul", "💎 Azul"),
    ("emerald", "💚 Emerald"),
    ("barca", "🔵🔴 Barça"),
    ("gta6", "🌴 GTA VI"),
    ("ets2", "🚛 Euro Truck"),
    ("navidad", "🎄 Navidad"),
]


def get_github_token():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    gh_exe = os.path.expandvars(r"%LOCALAPPDATA%\gh-cli\bin\gh.exe")
    if os.path.exists(gh_exe):
        try:
            out = subprocess.check_output([gh_exe, "auth", "token"], text=True, stderr=subprocess.DEVNULL).strip()
            if out:
                return out
        except Exception:
            pass
    return ""


def github_put_file(rel_path: str, content_bytes: bytes, message: str):
    """Sube o actualiza un archivo en mgbarcelonalive.github.io."""
    token = get_github_token()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{rel_path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MG-Barcelona-Live-Cloud-Server",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    sha = None
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing = json.loads(resp.read().decode("utf-8"))
            sha = existing.get("sha")
    except Exception:
        pass

    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha

    if token:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status in (200, 201)

    gh_exe = os.path.expandvars(r"%LOCALAPPDATA%\gh-cli\bin\gh.exe")
    if os.path.exists(gh_exe):
        proc = subprocess.Popen(
            [gh_exe, "api", f"repos/{GITHUB_REPO}/contents/{rel_path}", "--method", "PUT", "--input", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        proc.communicate(input=json.dumps(payload).encode("utf-8"))
        return proc.returncode == 0
    return False


def load_json_manifest(rel_path: str, default_val):
    for base in (BASE_DIR, WEB_DIR):
        p = base / rel_path.replace("/", os.sep)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    try:
        url = f"https://mgbarcelonalive.github.io/{rel_path}?t={int(time.time())}"
        req = urllib.request.Request(url, headers={"User-Agent": "MG-Cloud-Server"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return default_val


def save_json_manifest(rel_path: str, obj: dict, commit_msg: str):
    raw = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
    (BASE_DIR / rel_path.replace("/", os.sep)).write_bytes(raw)
    if WEB_DIR.exists():
        (WEB_DIR / rel_path.replace("/", os.sep)).write_bytes(raw)
    github_put_file(rel_path, raw, commit_msg)


class CloudRadioEngine:
    def __init__(self):
        self.clients = set()
        self.clients_lock = threading.Lock()
        self.current_title = "MG Barcelona Live · Emisión 24/7"
        self.skip_requested = False
        self.forced_file = None
        self.tracks_since_cuna = 0
        self.live_active = False
        self.ffmpeg_bin = self._find_ffmpeg()
        self.icecast_sock = None

    def _find_ffmpeg(self):
        p = shutil.which("ffmpeg")
        if p:
            return p
        local_candidates = glob.glob(os.path.expanduser(r"~\AppData\Local\CapCut\Apps\*\ffmpeg.exe"))
        if local_candidates:
            return local_candidates[-1]
        return "ffmpeg"

    def list_music(self):
        return [f.name for f in sorted(MUSIC_DIR.glob("*.mp3"))]

    def list_cunas(self):
        return [f.name for f in sorted(CUNAS_DIR.glob("*.mp3"))]

    def list_server_videos(self):
        vids = [f"videos/{f.name}" for f in sorted(VIDEOS_DIR.glob("*.mp4"))]
        if not vids:
            v_manifest = load_json_manifest("videos.json", {"videos": []})
            vids = v_manifest.get("videos", [])
        return vids

    def list_server_ads(self):
        p_manifest = load_json_manifest("publicidad.json", {"anuncios": []})
        return p_manifest.get("anuncios", [])

    def list_server_photos(self):
        f_manifest = load_json_manifest("eventos_fotos.json", {"fotos": [], "por_plantilla": {}})
        result = []
        por_tpl = f_manifest.get("por_plantilla", {})
        for tpl, items in por_tpl.items():
            for it in items:
                result.append({
                    "archivo": it.get("archivo", ""),
                    "titulo": it.get("titulo", ""),
                    "club": it.get("club", "Barcelona Club"),
                    "plantilla": tpl
                })
        for it in f_manifest.get("fotos", []):
            result.append({
                "archivo": it.get("archivo", ""),
                "titulo": it.get("titulo", ""),
                "club": it.get("club", "Barcelona Club"),
                "plantilla": "todas"
            })
        return result

    def add_client(self, wfile):
        with self.clients_lock:
            self.clients.add(wfile)

    def remove_client(self, wfile):
        with self.clients_lock:
            self.clients.discard(wfile)

    def _send_to_local_icecast(self, chunk: bytes):
        if self.icecast_sock is None:
            try:
                s = socket.create_connection(("127.0.0.1", 8000), timeout=1.5)
                auth = base64.b64encode(b"source:MGRadioSrc2026!").decode("ascii")
                headers = (
                    "SOURCE /stream HTTP/1.0\r\n"
                    f"Authorization: Basic {auth}\r\n"
                    "Content-Type: audio/mpeg\r\n"
                    "ice-name: MG Barcelona Live Cloud AutoDJ\r\n"
                    "ice-public: 1\r\n\r\n"
                )
                s.sendall(headers.encode("utf-8"))
                resp = s.recv(256)
                if b"200 OK" in resp:
                    self.icecast_sock = s
                else:
                    s.close()
            except Exception:
                self.icecast_sock = None

        if self.icecast_sock is not None:
            try:
                self.icecast_sock.sendall(chunk)
            except Exception:
                try:
                    self.icecast_sock.close()
                except Exception:
                    pass
                self.icecast_sock = None

    def broadcast_chunk(self, chunk: bytes):
        if not chunk:
            return
        self._send_to_local_icecast(chunk)
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
                try:
                    with open(next_file, "rb") as fp:
                        while not self.skip_requested and not self.live_active:
                            chunk = fp.read(4096)
                            if not chunk:
                                break
                            self.broadcast_chunk(chunk)
                            time.sleep(0.24)
                except Exception:
                    time.sleep(1.0)


ENGINE = CloudRadioEngine()


PANEL_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MG Barcelona Live · Herramienta Total en el Servidor</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&display=swap');
  :root { --bg:#07050f; --card:#120d24; --neon:#b44fff; --cyan:#00f0ff; --pink:#ff2d78; --gold:#f5c842; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:#fff; font-family:'Inter',sans-serif; padding:1.2rem; }
  .wrap { max-width:1280px; margin:0 auto; }
  .header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:1rem; padding:1.3rem 1.6rem; background:var(--card); border:2px solid rgba(0,240,255,0.45); border-radius:20px; box-shadow:0 0 30px rgba(180,79,255,0.25); margin-bottom:1.2rem; }
  .title { font-family:'Bebas Neue',sans-serif; font-size:2.3rem; letter-spacing:0.06em; background:linear-gradient(90deg,#fff,var(--gold),var(--pink)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .badge { display:inline-flex; align-items:center; gap:0.5rem; padding:0.45rem 1rem; border-radius:999px; background:rgba(0,240,255,0.12); border:1px solid var(--cyan); color:var(--cyan); font-size:0.8rem; font-weight:700; }
  .tabs { display:flex; gap:0.55rem; flex-wrap:wrap; margin-bottom:1.2rem; }
  .tab-btn { padding:0.75rem 1.3rem; border-radius:999px; border:1px solid rgba(255,255,255,0.18); background:var(--card); color:#fff; font-weight:700; font-size:0.86rem; cursor:pointer; transition:0.2s; }
  .tab-btn.active { background:linear-gradient(135deg,var(--neon),var(--pink)); border-color:transparent; box-shadow:0 0 20px rgba(255,45,120,0.4); }
  .tab-panel { display:none; }
  .tab-panel.active { display:block; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(330px, 1fr)); gap:1.3rem; }
  .card { background:var(--card); border:1px solid rgba(255,255,255,0.12); border-radius:18px; padding:1.4rem; }
  .card h2 { font-family:'Bebas Neue',sans-serif; font-size:1.65rem; color:var(--gold); letter-spacing:0.05em; margin-bottom:0.85rem; }
  .stat-row { display:flex; justify-content:space-between; padding:0.6rem 0; border-bottom:1px solid rgba(255,255,255,0.07); font-size:0.88rem; }
  .btn { display:inline-flex; align-items:center; justify-content:center; gap:0.4rem; padding:0.65rem 1.1rem; border-radius:999px; border:1px solid rgba(255,255,255,0.2); background:rgba(255,255,255,0.06); color:#fff; font-weight:600; font-size:0.83rem; cursor:pointer; transition:0.2s; text-decoration:none; }
  .btn:hover { border-color:var(--cyan); box-shadow:0 0 15px rgba(0,240,255,0.35); }
  .btn-primary { background:linear-gradient(135deg,var(--neon),var(--pink)); border:none; }
  .track-list { max-height:310px; overflow-y:auto; margin-top:0.7rem; border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:0.45rem; }
  .track-item { display:flex; align-items:center; justify-content:space-between; gap:0.5rem; padding:0.5rem 0.65rem; border-radius:8px; font-size:0.82rem; }
  .track-item:hover { background:rgba(255,255,255,0.06); }
  .tpl-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(165px, 1fr)); gap:0.75rem; margin-top:0.8rem; }
  .tpl-btn { padding:0.9rem 0.7rem; border-radius:14px; border:1px solid rgba(255,255,255,0.16); background:#0b0718; color:#fff; font-weight:700; font-size:0.85rem; cursor:pointer; text-align:center; transition:0.2s; }
  .tpl-btn:hover, .tpl-btn.active { border-color:var(--cyan); background:rgba(0,240,255,0.14); box-shadow:0 0 18px rgba(0,240,255,0.3); }
  .photo-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:0.8rem; max-height:440px; overflow-y:auto; padding:0.4rem; }
  .photo-card { background:#090614; border:1px solid rgba(255,255,255,0.12); border-radius:12px; overflow:hidden; text-align:center; padding-bottom:0.5rem; }
  .photo-card img { width:100%; height:120px; object-fit:cover; display:block; }
  .photo-card p { font-size:0.74rem; padding:0.35rem 0.4rem 0; color:rgba(255,255,255,0.85); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  input[type="file"], input[type="password"], input[type="text"], select { width:100%; padding:0.65rem; border-radius:10px; border:1px solid rgba(255,255,255,0.2); background:#090614; color:#fff; margin-bottom:0.75rem; }
  audio { width:100%; margin-top:0.8rem; border-radius:999px; }
  .url-box { background:#090614; border:1px solid rgba(0,240,255,0.35); padding:0.7rem; border-radius:10px; font-family:monospace; font-size:0.8rem; color:var(--cyan); word-break:break-all; margin-top:0.5rem; }
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div>
      <div class="title">MG BARCELONA LIVE · PANEL DEL SERVIDOR 24/7</div>
      <p style="font-size:0.84rem;color:rgba(255,255,255,0.7);">Control Total en el Servidor: Radio 24h, Plantillas Web, Vídeos Musicales, Publicidad y Fotografías</p>
    </div>
    <div style="display:flex;gap:0.6rem;align-items:center;">
      <a class="btn" href="https://mgbarcelonalive.github.io/" target="_blank">🌐 Ver Web Pública</a>
      <div class="badge">● SERVIDOR ACTIVO</div>
    </div>
  </div>

  <div style="margin-bottom:1rem;display:flex;align-items:center;gap:0.8rem;flex-wrap:wrap;background:var(--card);padding:0.75rem 1.2rem;border-radius:14px;border:1px solid rgba(255,255,255,0.1);">
    <span style="font-size:0.83rem;color:var(--gold);font-weight:700;">🔑 Clave del Servidor:</span>
    <input type="password" id="adminPass" value="mg2026" style="width:150px;margin:0;padding:0.4rem 0.7rem;">
    <span id="globalMsg" style="font-size:0.83rem;color:var(--cyan);"></span>
  </div>

  <!-- 4 Pestañas Completas -->
  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('tab-musica', this)">🎵 1. Radio, Música y Cuñas</button>
    <button class="tab-btn" onclick="showTab('tab-web', this)">🎨 2. Diseño Web y Plantillas</button>
    <button class="tab-btn" onclick="showTab('tab-videos', this)">🎬 3. Vídeos y Publicidad (<span id="tabVidCount">0</span>)</button>
    <button class="tab-btn" onclick="showTab('tab-fotos', this)">📸 4. Fotografías Moisés Gallardo (<span id="tabFotoCount">0</span>)</button>
  </div>

  <!-- PESTAÑA 1: MÚSICA Y CUÑAS -->
  <div id="tab-musica" class="tab-panel active">
    <div class="grid">
      <div class="card">
        <h2>📡 Emisión en Vivo desde el Servidor</h2>
        <div class="stat-row"><span>Sonando ahora:</span><strong id="nowPlaying" style="color:var(--cyan);">Cargando...</strong></div>
        <div class="stat-row"><span>Modo:</span><strong id="streamMode">AutoDJ 24/7 (Sin Virtual DJ)</strong></div>
        <div class="stat-row"><span>Oyentes en el servidor:</span><strong id="listenersCount" style="color:var(--gold);">0</strong></div>
        <div style="margin-top:1rem;display:flex;gap:0.6rem;flex-wrap:wrap;">
          <button class="btn btn-primary" onclick="skipTrack()">⏭ Siguiente Canción</button>
          <a class="btn" href="/stream" target="_blank">🔗 Escuchar Stream</a>
        </div>
        <audio controls preload="none" src="/stream"></audio>
        <p style="font-size:0.76rem;color:rgba(255,255,255,0.5);margin-top:0.8rem;">Enlace directo del stream de este servidor:</p>
        <div class="url-box" id="streamUrlBox"></div>
      </div>

      <div class="card">
        <h2>☁️ Subir Canciones MP3 o Cuñas</h2>
        <form onsubmit="uploadAudio(event)">
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Destino en el servidor:</label>
          <select id="uploadType">
            <option value="musica">🎵 Carpeta de Música 24/7 (.mp3)</option>
            <option value="cunas">🔊 Carpeta de Cuñas de Radio (.mp3)</option>
          </select>
          <input type="file" id="audioFiles" accept=".mp3" multiple required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir MP3 al Servidor</button>
        </form>
        <p id="uploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>

      <div class="card">
        <h2>🎵 Canciones en el Servidor (<span id="musicCount">0</span>)</h2>
        <div class="track-list" id="musicList"></div>
      </div>

      <div class="card">
        <h2>🔊 Cuñas de Radio (<span id="cunasCount">0</span>)</h2>
        <div class="track-list" id="cunasList"></div>
      </div>
    </div>
  </div>

  <!-- PESTAÑA 2: CONTROL DE LA WEB Y PLANTILLAS -->
  <div id="tab-web" class="tab-panel">
    <div class="grid">
      <div class="card" style="grid-column: 1 / -1;">
        <h2>🎨 Cambiar Plantilla de la Web en Tiempo Real (mgbarcelonalive.github.io)</h2>
        <p style="font-size:0.85rem;color:rgba(255,255,255,0.7);margin-bottom:0.6rem;">
          Plantilla activa en la web: <strong id="currentTplLabel" style="color:var(--cyan);">principal</strong>.
          Pulsa cualquier diseño para activarlo al instante en móviles y ordenadores:
        </p>
        <div class="tpl-grid" id="tplGrid"></div>
      </div>

      <div class="card" style="grid-column: 1 / -1;">
        <h2>🔗 Conectar URL Fija del Servidor con la Web Pública</h2>
        <div style="display:flex;gap:0.7rem;flex-wrap:wrap;">
          <input type="text" id="customStreamUrl" style="flex:1;min-width:260px;margin:0;">
          <button class="btn btn-primary" onclick="updateWebStreamUrl()">🌐 Publicar este Stream en la Web</button>
        </div>
      </div>
    </div>
  </div>

  <!-- PESTAÑA 3: VÍDEOS MUSICALES Y PUBLICIDAD -->
  <div id="tab-videos" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>🎬 Subir Vídeo Musical o Anuncio (.mp4)</h2>
        <form onsubmit="uploadWebVideo(event)">
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Categoría del vídeo:</label>
          <select id="videoKind">
            <option value="videos">🎬 Vídeo Musical (Moda & House)</option>
            <option value="publicidad">📣 Anuncio de Publicidad de la Radio</option>
          </select>
          <input type="file" id="webVideoFile" accept=".mp4" required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir MP4 al Servidor y a la Web</button>
        </form>
        <p id="videoUploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>

      <div class="card">
        <h2>📺 Vídeos Musicales en el Servidor (<span id="webVideosCount">0</span>)</h2>
        <div class="track-list" id="webVideosList"></div>
      </div>

      <div class="card">
        <h2>📣 Publicidad en Vídeo (<span id="webAdsCount">0</span>)</h2>
        <div class="track-list" id="webAdsList"></div>
      </div>
    </div>
  </div>

  <!-- PESTAÑA 4: FOTOGRAFÍAS MOISÉS GALLARDO -->
  <div id="tab-fotos" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>📸 Subir Nueva Fotografía · Moisés Gallardo</h2>
        <form onsubmit="uploadWebPhoto(event)">
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Título de la foto / Evento:</label>
          <input type="text" id="photoTitle" placeholder="Ej: Saturgays Barcelona" required>
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Club / Sala:</label>
          <input type="text" id="photoClub" value="Barcelona Club" required>
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Plantilla destino:</label>
          <select id="photoTpl">
            <option value="principal">🏆 Plantilla Principal</option>
            <option value="todas">🌟 Todas las Plantillas</option>
          </select>
          <input type="file" id="webPhotoFile" accept=".jpg,.jpeg,.png,.webp" multiple required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir Fotografía(s) al Servidor y Web</button>
        </form>
        <p id="photoUploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>

      <div class="card" style="grid-column: span 2;">
        <h2>🖼️ Galería Fotográfica en el Servidor (<span id="photosCount">0</span> fotos)</h2>
        <div class="photo-grid" id="photosGrid"></div>
      </div>
    </div>
  </div>
</div>

<script>
document.getElementById('streamUrlBox').textContent = window.location.origin + '/stream';
document.getElementById('customStreamUrl').value = window.location.origin + '/stream';

function showTab(id, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}

function setMsg(text) {
  document.getElementById('globalMsg').textContent = text;
}

async function refreshStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('nowPlaying').textContent = d.current_title || 'Sin pista';
    document.getElementById('listenersCount').textContent = d.listeners;
    document.getElementById('musicCount').textContent = d.music.length;
    document.getElementById('cunasCount').textContent = d.cunas.length;
    document.getElementById('currentTplLabel').textContent = d.current_template || 'principal';

    const mEl = document.getElementById('musicList');
    mEl.innerHTML = d.music.length ? d.music.map(m =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">🎵 ${m}</span><button class="btn" style="padding:0.25rem 0.6rem;font-size:0.75rem;" onclick="playSpecific('musica', '${m.replace(/'/g,"\\'")}')">▶ Poner</button></div>`
    ).join('') : '<p style="font-size:0.8rem;color:rgba(255,255,255,0.4);padding:0.5rem;">Sube archivos MP3 para que suenen 24/7.</p>';

    const cEl = document.getElementById('cunasList');
    cEl.innerHTML = d.cunas.map(c =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">🔊 ${c}</span><button class="btn" style="padding:0.25rem 0.6rem;font-size:0.75rem;" onclick="playSpecific('cunas', '${c.replace(/'/g,"\\'")}')">🔊 Lanzar</button></div>`
    ).join('');

    // Plantillas
    document.getElementById('tplGrid').innerHTML = (d.templates || []).map(t =>
      `<button class="tpl-btn ${t.id === d.current_template ? 'active' : ''}" onclick="setWebTemplate('${t.id}')">${t.label}</button>`
    ).join('');

    // Vídeos y Anuncios
    const vList = d.web_videos || [];
    const aList = d.web_ads || [];
    document.getElementById('webVideosCount').textContent = vList.length;
    document.getElementById('webAdsCount').textContent = aList.length;
    document.getElementById('tabVidCount').textContent = vList.length + aList.length;

    document.getElementById('webVideosList').innerHTML = vList.map((v, i) =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">🎬 ${i+1}. ${v}</span><a class="btn" style="padding:0.2rem 0.55rem;font-size:0.73rem;" href="/${v}" target="_blank">▶ Ver</a></div>`
    ).join('');

    document.getElementById('webAdsList').innerHTML = aList.map((a, i) =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">📣 ${i+1}. ${a.nombre || a.archivo}</span><a class="btn" style="padding:0.2rem 0.55rem;font-size:0.73rem;" href="/${a.archivo}" target="_blank">▶ Ver</a></div>`
    ).join('');

    // Fotografías Moisés Gallardo
    const pList = d.web_photos || [];
    document.getElementById('photosCount').textContent = pList.length;
    document.getElementById('tabFotoCount').textContent = pList.length;
    document.getElementById('photosGrid').innerHTML = pList.map(p =>
      `<div class="photo-card">
         <a href="/${p.archivo}" target="_blank"><img src="/${p.archivo}" loading="lazy" alt="${p.titulo}"></a>
         <p title="${p.titulo}">📸 ${p.titulo || 'Foto MG'}</p>
         <p style="color:var(--gold);font-size:0.68rem;">${p.club || ''}</p>
       </div>`
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

async function uploadAudio(e) {
  e.preventDefault();
  const status = document.getElementById('uploadStatus');
  const files = document.getElementById('audioFiles').files;
  if (!files.length) return;
  const pass = document.getElementById('adminPass').value;
  const type = document.getElementById('uploadType').value;
  try {
    let subidos = 0;
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      status.textContent = `Subiendo (${i+1}/${files.length}): ${f.name}...`;
      const url = `/api/upload?type=${encodeURIComponent(type)}&name=${encodeURIComponent(f.name)}`;
      const r = await fetch(url, { method: 'POST', headers: { 'X-Admin-Pass': pass }, body: f });
      const res = await r.json();
      if (!res.ok) { status.textContent = res.message || 'Error'; return; }
      subidos++;
    }
    status.textContent = `✅ ${subidos} archivo(s) subidos al servidor`;
    document.getElementById('audioFiles').value = '';
    refreshStatus();
  } catch (err) {
    status.textContent = 'Error al subir archivo';
  }
}

async function setWebTemplate(tplId) {
  setMsg(`Cambiando web a plantilla "${tplId}"...`);
  const pass = document.getElementById('adminPass').value;
  const r = await fetch('/api/set_template', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Pass': pass },
    body: JSON.stringify({ plantilla: tplId })
  });
  const res = await r.json();
  setMsg(res.message || '');
  refreshStatus();
}

async function updateWebStreamUrl() {
  const streamUrl = document.getElementById('customStreamUrl').value.trim();
  if (!streamUrl) return;
  setMsg('Actualizando URL del stream en la web pública...');
  const pass = document.getElementById('adminPass').value;
  const r = await fetch('/api/set_stream_url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Pass': pass },
    body: JSON.stringify({ stream_url: streamUrl })
  });
  const res = await r.json();
  setMsg(res.message || '');
}

async function uploadWebVideo(e) {
  e.preventDefault();
  const status = document.getElementById('videoUploadStatus');
  const files = document.getElementById('webVideoFile').files;
  if (!files.length) return;
  const f = files[0];
  const kind = document.getElementById('videoKind').value;
  const pass = document.getElementById('adminPass').value;
  status.textContent = `Subiendo ${f.name} al servidor y a la web...`;
  const r = await fetch(`/api/upload_web_video?kind=${encodeURIComponent(kind)}&name=${encodeURIComponent(f.name)}`, {
    method: 'POST',
    headers: { 'X-Admin-Pass': pass },
    body: f
  });
  const res = await r.json();
  status.textContent = res.message || '';
  document.getElementById('webVideoFile').value = '';
  refreshStatus();
}

async function uploadWebPhoto(e) {
  e.preventDefault();
  const status = document.getElementById('photoUploadStatus');
  const files = document.getElementById('webPhotoFile').files;
  if (!files.length) return;
  const title = document.getElementById('photoTitle').value.trim();
  const club = document.getElementById('photoClub').value.trim();
  const tpl = document.getElementById('photoTpl').value;
  const pass = document.getElementById('adminPass').value;
  let subidas = 0;
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    status.textContent = `Subiendo foto (${i+1}/${files.length}): ${f.name}...`;
    const q = `name=${encodeURIComponent(f.name)}&title=${encodeURIComponent(title)}&club=${encodeURIComponent(club)}&tpl=${encodeURIComponent(tpl)}`;
    const r = await fetch(`/api/upload_web_photo?${q}`, {
      method: 'POST',
      headers: { 'X-Admin-Pass': pass },
      body: f
    });
    const res = await r.json();
    if (!res.ok) { status.textContent = res.message || 'Error'; return; }
    subidas++;
  }
  status.textContent = `✅ ${subidas} fotografía(s) añadidas al servidor y a la galería web`;
  document.getElementById('webPhotoFile').value = '';
  refreshStatus();
}

refreshStatus();
setInterval(refreshStatus, 3500);
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Admin-Pass")

    def _send_json(self, code: int, obj: dict):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._send_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/panel"):
            body = PANEL_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/status":
            tpl_info = load_json_manifest("plantilla_live.json", {"plantilla": "principal"})
            data = {
                "current_title": ENGINE.current_title,
                "live_active": ENGINE.live_active,
                "listeners": len(ENGINE.clients),
                "music": ENGINE.list_music(),
                "cunas": ENGINE.list_cunas(),
                "current_template": tpl_info.get("plantilla", "principal"),
                "templates": [{"id": k, "label": v} for k, v in PLANTILLAS_DISPONIBLES],
                "web_videos": ENGINE.list_server_videos(),
                "web_ads": ENGINE.list_server_ads(),
                "web_photos": ENGINE.list_server_photos(),
            }
            self._send_json(200, data)
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

        # Servir archivos multimedia del servidor (videos/, publicidad/, eventos_fotos/)
        if path.startswith(("/videos/", "/publicidad/", "/eventos_fotos/")):
            rel = path.lstrip("/")
            for root_candidate in (BASE_DIR, WEB_DIR):
                local_target = (root_candidate / rel.replace("/", os.sep)).resolve()
                if local_target.exists() and local_target.is_file():
                    ctype, _ = mimetypes.guess_type(str(local_target))
                    data = local_target.read_bytes()
                    self.send_response(200)
                    self._send_cors()
                    self.send_header("Content-Type", ctype or "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            # Redirigir a GitHub Pages CDN si no está en disco local
            self.send_response(302)
            self.send_header("Location", f"https://mgbarcelonalive.github.io/{rel}")
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/next":
            ENGINE.skip_requested = True
            self._send_json(200, {"ok": True})
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
            self._send_json(200, {"ok": True})
            return

        if path == "/api/upload":
            qs = parse_qs(parsed.query)
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
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

            self._send_json(200, {"ok": True, "message": f"✅ {fname} subido al servidor"})
            return

        if path == "/api/set_template":
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            tpl = body.get("plantilla", "principal")
            live_obj = {"plantilla": tpl, "ts": int(time.time() * 1000)}
            save_json_manifest("plantilla_live.json", live_obj, f"Activar plantilla en vivo: {tpl}")

            if WEB_DIR.exists():
                src_tpl = WEB_DIR / "plantillas" / f"{tpl}.html"
                if src_tpl.exists():
                    tpl_bytes = src_tpl.read_bytes()
                    (WEB_DIR / "index.html").write_bytes(tpl_bytes)
                    github_put_file("index.html", tpl_bytes, f"Cambiar plantilla web a {tpl}")

            self._send_json(200, {"ok": True, "message": f"✅ Plantilla «{tpl}» activada en vivo en la web"})
            return

        if path == "/api/set_stream_url":
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            new_url = body.get("stream_url", "").strip()
            if not new_url:
                self._send_json(400, {"ok": False, "message": "URL vacía"})
                return

            import re
            pattern = re.compile(r"const\s+STREAM_URL\s*=\s*'[^']*';")
            updated = 0
            if WEB_DIR.exists():
                for html_file in [WEB_DIR / "index.html", *(WEB_DIR / "plantillas").glob("*.html")]:
                    if html_file.exists():
                        txt = html_file.read_text(encoding="utf-8", errors="ignore")
                        new_txt = pattern.sub(f"const STREAM_URL = '{new_url}';", txt)
                        if new_txt != txt:
                            html_file.write_text(new_txt, encoding="utf-8")
                            rel = html_file.relative_to(WEB_DIR).as_posix()
                            github_put_file(rel, new_txt.encode("utf-8"), f"Conectar stream cloud: {new_url}")
                            updated += 1
            self._send_json(200, {"ok": True, "message": f"✅ Stream conectado en la web ({updated} archivos actualizados)"})
            return

        if path == "/api/upload_web_video":
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
                return
            qs = parse_qs(parsed.query)
            kind = qs.get("kind", ["videos"])[0]
            fname = Path(unquote(qs.get("name", ["video.mp4"])[0])).name
            if not fname.lower().endswith(".mp4"):
                fname += ".mp4"
            length = int(self.headers.get("Content-Length", "0"))
            video_bytes = self.rfile.read(length)

            if kind == "publicidad":
                rel_vid = f"publicidad/{fname}"
                (PUBLICIDAD_DIR / fname).write_bytes(video_bytes)
                if WEB_DIR.exists():
                    (WEB_DIR / "publicidad" / fname).write_bytes(video_bytes)
                github_put_file(rel_vid, video_bytes, f"Subir anuncio de video {fname}")
                pub_info = load_json_manifest("publicidad.json", {"intervalo": 10, "anuncios": []})
                anuncios = pub_info.get("anuncios", [])
                if not any(a.get("archivo") == rel_vid for a in anuncios):
                    anuncios.append({"archivo": rel_vid, "tipo": "video", "nombre": fname})
                pub_info["anuncios"] = anuncios
                save_json_manifest("publicidad.json", pub_info, f"Añadir anuncio {fname}")
            else:
                rel_vid = f"videos/{fname}"
                (VIDEOS_DIR / fname).write_bytes(video_bytes)
                if WEB_DIR.exists():
                    (WEB_DIR / "videos" / fname).write_bytes(video_bytes)
                github_put_file(rel_vid, video_bytes, f"Subir nuevo video musical {fname}")
                vids_info = load_json_manifest("videos.json", {"total": 0, "videos": []})
                vlist = vids_info.get("videos", [])
                if rel_vid not in vlist:
                    vlist.append(rel_vid)
                save_json_manifest("videos.json", {"total": len(vlist), "videos": vlist}, f"Añadir vídeo {fname}")

            self._send_json(200, {"ok": True, "message": f"✅ Vídeo «{fname}» subido al servidor y publicado en la web"})
            return

        if path == "/api/upload_web_photo":
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
                return
            qs = parse_qs(parsed.query)
            fname = Path(unquote(qs.get("name", ["foto.jpg"])[0])).name
            title = unquote(qs.get("title", [Path(fname).stem])[0])
            club = unquote(qs.get("club", ["Barcelona Club"])[0])
            tpl = unquote(qs.get("tpl", ["principal"])[0])
            length = int(self.headers.get("Content-Length", "0"))
            photo_bytes = self.rfile.read(length)

            sub_folder = "principal" if tpl == "todas" else tpl
            rel_photo = f"eventos_fotos/{sub_folder}/{fname}"
            target_local = FOTOS_DIR / sub_folder / fname
            target_local.parent.mkdir(parents=True, exist_ok=True)
            target_local.write_bytes(photo_bytes)

            if WEB_DIR.exists():
                w_target = WEB_DIR / "eventos_fotos" / sub_folder / fname
                w_target.parent.mkdir(parents=True, exist_ok=True)
                w_target.write_bytes(photo_bytes)

            github_put_file(rel_photo, photo_bytes, f"Subir fotografia Moises Gallardo: {fname}")

            fotos_info = load_json_manifest("eventos_fotos.json", {"fotos": [], "por_plantilla": {}})
            entry = {"archivo": rel_photo, "titulo": title, "club": club}
            if tpl == "todas":
                fotos_info.setdefault("fotos", []).append(entry)
            else:
                fotos_info.setdefault("por_plantilla", {}).setdefault(tpl, []).append(entry)
            save_json_manifest("eventos_fotos.json", fotos_info, f"Actualizar galeria con {fname}")

            self._send_json(200, {"ok": True, "message": f"✅ Fotografía «{fname}» subida al servidor y publicada"})
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    t = threading.Thread(target=ENGINE.autodj_loop, daemon=True)
    t.start()
    print(f"============================================================")
    print(f" MG BARCELONA LIVE - SERVIDOR Y HERRAMIENTA TOTAL 24/7")
    print(f" Panel de Control  : http://localhost:{PORT}/panel")
    print(f" Stream de Audio   : http://localhost:{PORT}/stream")
    print(f"============================================================")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), RadioHTTPHandler)
    server.serve_forever()
