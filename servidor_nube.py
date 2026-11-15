#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MG BARCELONA LIVE - SERVIDOR DE RADIO EN LA NUBE + HERRAMIENTA STUDIO TOTAL 24/7
================================================================================
Incluye TODAS las funciones de la herramienta de escritorio dentro del servidor:
  - Acceso protegido con contraseña (por defecto: mg2026)
  - Subida de CARPETAS ENTERAS llenas de música (.mp3) y archivos sueltos
  - 9 Pestañas completas:
      1. 📡 Emisión 24/7 y Biblioteca de Música (AutoDJ sin Virtual DJ)
      2. 🎙️ Presentador Virtual IA y Cuñas de Radio (cunas/ y cunas.json)
      3. 🎨 Plantillas y Diseño de la Web en Vivo (16 plantillas)
      4. 🎬 Vídeos Musicales Automáticos (videos/ y videos.json)
      5. 📣 Publicidad y Anuncios de la Radio (publicidad/ y publicidad.json)
      6. 📸 Fotografías · Moisés Gallardo (eventos_fotos/ y eventos_fotos.json)
      7. 🌌 Vídeos de Fondo de las Plantillas (videos/fondos_principal/)
      8. 🤝 Sponsors y Patrocinadores (sponsors/)
      9. ⚙️ Capacidad Técnica del Servidor (CPU, RAM, Almacenamiento y Logs)
  - Botón global «🚀 ACTUALIZAR TODA LA WEB DE LA RADIO»
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
import platform
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
FONDOS_DIR = VIDEOS_DIR / "fondos_principal"
PUBLICIDAD_DIR = BASE_DIR / "publicidad"
FOTOS_DIR = BASE_DIR / "eventos_fotos"
SPONSORS_DIR = BASE_DIR / "sponsors"

for _d in (MUSIC_DIR, CUNAS_DIR, VIDEOS_DIR, FONDOS_DIR, PUBLICIDAD_DIR, FOTOS_DIR, SPONSORS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("PORT", "8080"))
ADMIN_PASS = os.environ.get("MG_ADMIN_PASS", "mg2026")
CUNA_INTERVAL = int(os.environ.get("MG_CUNA_INTERVAL", "3"))
GITHUB_REPO = "mgbarcelonalive/mgbarcelonalive.github.io"
START_TIME = time.time()
SERVER_LOGS = ["[OK] Servidor MG Barcelona Live 24/7 iniciado correctamente."]

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


def add_log(msg: str):
    ts = time.strftime("%H:%M:%S")
    SERVER_LOGS.append(f"[{ts}] {msg}")
    if len(SERVER_LOGS) > 120:
        del SERVER_LOGS[0]


def get_server_specs():
    """Obtiene capacidad técnica real del servidor: CPU, Memoria RAM y Almacenamiento."""
    cpu_cores = os.cpu_count() or 2
    arch = f"{platform.system()} {platform.release()} ({platform.machine()})"

    # Almacenamiento en disco
    try:
        du = shutil.disk_usage(str(BASE_DIR))
        disk_total_gb = round(du.total / (1024 ** 3), 2)
        disk_used_gb = round(du.used / (1024 ** 3), 2)
        disk_free_gb = round(du.free / (1024 ** 3), 2)
    except Exception:
        disk_total_gb, disk_used_gb, disk_free_gb = 50.0, 1.2, 48.8

    # Memoria RAM
    ram_total_gb = 16.0
    ram_free_gb = 14.2
    try:
        if os.path.exists("/proc/meminfo"):
            meminfo = Path("/proc/meminfo").read_text()
            for line in meminfo.splitlines():
                if line.startswith("MemTotal:"):
                    ram_total_gb = round(int(line.split()[1]) / (1024 ** 2), 2)
                elif line.startswith("MemAvailable:"):
                    ram_free_gb = round(int(line.split()[1]) / (1024 ** 2), 2)
        elif sys.platform == "win32":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            ram_total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
            ram_free_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
    except Exception:
        pass

    uptime_min = int((time.time() - START_TIME) // 60)
    return {
        "cpu_cores": cpu_cores,
        "arch": arch,
        "ram_total_gb": ram_total_gb,
        "ram_free_gb": ram_free_gb,
        "disk_total_gb": disk_total_gb,
        "disk_used_gb": disk_used_gb,
        "disk_free_gb": disk_free_gb,
        "uptime_min": uptime_min,
    }


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
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={**headers, "Content-Type": "application/json"},
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                add_log(f"Publicado en web GitHub: {rel_path}")
                return resp.status in (200, 201)
        except Exception as e:
            add_log(f"Aviso GitHub API ({rel_path}): {e}")

    gh_exe = os.path.expandvars(r"%LOCALAPPDATA%\gh-cli\bin\gh.exe")
    if os.path.exists(gh_exe):
        proc = subprocess.Popen(
            [gh_exe, "api", f"repos/{GITHUB_REPO}/contents/{rel_path}", "--method", "PUT", "--input", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        proc.communicate(input=json.dumps(payload).encode("utf-8"))
        if proc.returncode == 0:
            add_log(f"Publicado en web GitHub (CLI): {rel_path}")
            return True
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
        self.cuna_every_n = CUNA_INTERVAL
        self.cunas_enabled = True
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
        return [f.name for f in sorted(MUSIC_DIR.rglob("*.mp3"))]

    def list_cunas(self):
        return [f.name for f in sorted(CUNAS_DIR.glob("*.mp3"))]

    def list_server_videos(self):
        vids = [f"videos/{f.name}" for f in sorted(VIDEOS_DIR.glob("*.mp4"))]
        if not vids:
            v_manifest = load_json_manifest("videos.json", {"videos": []})
            vids = v_manifest.get("videos", [])
        return vids

    def list_bg_videos(self):
        bgs = [f"videos/fondos_principal/{f.name}" for f in sorted(FONDOS_DIR.glob("*.mp4"))]
        if not bgs and WEB_DIR.exists() and (WEB_DIR / "videos" / "fondos_principal").exists():
            bgs = [f"videos/fondos_principal/{f.name}" for f in sorted((WEB_DIR / "videos" / "fondos_principal").glob("*.mp4"))]
        return bgs

    def list_sponsors(self):
        sps = [f"sponsors/{f.name}" for f in sorted(SPONSORS_DIR.glob("*.*")) if f.name.lower() != "desktop.ini"]
        if not sps and WEB_DIR.exists() and (WEB_DIR / "sponsors").exists():
            sps = [f"sponsors/{f.name}" for f in sorted((WEB_DIR / "sponsors").glob("*.*")) if f.name.lower() != "desktop.ini"]
        return sps

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

        music_files = sorted(MUSIC_DIR.rglob("*.mp3"))
        cuna_files = sorted(CUNAS_DIR.glob("*.mp3"))

        if self.cunas_enabled and cuna_files and (self.tracks_since_cuna >= self.cuna_every_n or not music_files):
            self.tracks_since_cuna = 0
            chosen = random.choice(cuna_files)
            self.current_title = f"Cuña Oficial · {chosen.stem}"
            add_log(f"Reproduciendo cuña: {chosen.name}")
            return chosen

        if music_files:
            self.tracks_since_cuna += 1
            chosen = random.choice(music_files)
            self.current_title = chosen.stem.replace("_", " ")
            add_log(f"Reproduciendo canción: {chosen.name}")
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
<title>MG Barcelona Live · Estudio Total en el Servidor 24/7</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&display=swap');
  :root { --bg:#07050f; --card:#120d24; --neon:#b44fff; --cyan:#00f0ff; --pink:#ff2d78; --gold:#f5c842; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:#fff; font-family:'Inter',sans-serif; padding:1rem; }
  .wrap { max-width:1360px; margin:0 auto; }

  /* Pantalla de Login con Contraseña */
  #loginOverlay { position:fixed; inset:0; z-index:9999; background:radial-gradient(circle at center, #1a0f36 0%, #07050f 100%); display:flex; align-items:center; justify-content:center; padding:1.2rem; }
  .login-box { background:var(--card); border:2px solid var(--cyan); border-radius:24px; max-width:420px; width:100%; padding:2.2rem 1.8rem; text-align:center; box-shadow:0 0 50px rgba(180,79,255,0.45); }
  .login-box h1 { font-family:'Bebas Neue',sans-serif; font-size:2.6rem; letter-spacing:0.06em; background:linear-gradient(90deg,#fff,var(--gold),var(--pink)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0.4rem; }

  .header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:1rem; padding:1.2rem 1.5rem; background:var(--card); border:2px solid rgba(0,240,255,0.45); border-radius:20px; box-shadow:0 0 30px rgba(180,79,255,0.25); margin-bottom:1rem; }
  .title { font-family:'Bebas Neue',sans-serif; font-size:2.2rem; letter-spacing:0.06em; background:linear-gradient(90deg,#fff,var(--gold),var(--pink)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .badge { display:inline-flex; align-items:center; gap:0.5rem; padding:0.45rem 1rem; border-radius:999px; background:rgba(0,240,255,0.12); border:1px solid var(--cyan); color:var(--cyan); font-size:0.8rem; font-weight:700; }
  .tabs { display:flex; gap:0.45rem; flex-wrap:wrap; margin-bottom:1.1rem; }
  .tab-btn { padding:0.65rem 1.05rem; border-radius:999px; border:1px solid rgba(255,255,255,0.18); background:var(--card); color:#fff; font-weight:700; font-size:0.8rem; cursor:pointer; transition:0.2s; }
  .tab-btn.active { background:linear-gradient(135deg,var(--neon),var(--pink)); border-color:transparent; box-shadow:0 0 18px rgba(255,45,120,0.4); }
  .tab-panel { display:none; }
  .tab-panel.active { display:block; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(330px, 1fr)); gap:1.2rem; }
  .card { background:var(--card); border:1px solid rgba(255,255,255,0.12); border-radius:18px; padding:1.35rem; }
  .card h2 { font-family:'Bebas Neue',sans-serif; font-size:1.6rem; color:var(--gold); letter-spacing:0.05em; margin-bottom:0.8rem; }
  .stat-row { display:flex; justify-content:space-between; padding:0.55rem 0; border-bottom:1px solid rgba(255,255,255,0.07); font-size:0.86rem; }
  .btn { display:inline-flex; align-items:center; justify-content:center; gap:0.4rem; padding:0.65rem 1.1rem; border-radius:999px; border:1px solid rgba(255,255,255,0.2); background:rgba(255,255,255,0.06); color:#fff; font-weight:600; font-size:0.82rem; cursor:pointer; transition:0.2s; text-decoration:none; }
  .btn:hover { border-color:var(--cyan); box-shadow:0 0 15px rgba(0,240,255,0.35); }
  .btn-primary { background:linear-gradient(135deg,var(--neon),var(--pink)); border:none; }
  .btn-gold { background:linear-gradient(135deg,#f5c842,#ff2d78); border:none; color:#fff; font-weight:700; }
  .track-list { max-height:310px; overflow-y:auto; margin-top:0.7rem; border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:0.45rem; }
  .track-item { display:flex; align-items:center; justify-content:space-between; gap:0.5rem; padding:0.48rem 0.65rem; border-radius:8px; font-size:0.81rem; }
  .track-item:hover { background:rgba(255,255,255,0.06); }
  .tpl-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(160px, 1fr)); gap:0.7rem; margin-top:0.8rem; }
  .tpl-btn { padding:0.85rem 0.65rem; border-radius:14px; border:1px solid rgba(255,255,255,0.16); background:#0b0718; color:#fff; font-weight:700; font-size:0.84rem; cursor:pointer; text-align:center; transition:0.2s; }
  .tpl-btn:hover, .tpl-btn.active { border-color:var(--cyan); background:rgba(0,240,255,0.14); box-shadow:0 0 18px rgba(0,240,255,0.3); }
  .photo-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(145px, 1fr)); gap:0.75rem; max-height:440px; overflow-y:auto; padding:0.4rem; }
  .photo-card { background:#090614; border:1px solid rgba(255,255,255,0.12); border-radius:12px; overflow:hidden; text-align:center; padding-bottom:0.45rem; }
  .photo-card img { width:100%; height:115px; object-fit:cover; display:block; }
  .photo-card p { font-size:0.73rem; padding:0.35rem 0.4rem 0; color:rgba(255,255,255,0.85); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  input[type="file"], input[type="password"], input[type="text"], input[type="number"], select { width:100%; padding:0.6rem; border-radius:10px; border:1px solid rgba(255,255,255,0.2); background:#090614; color:#fff; margin-bottom:0.7rem; }
  audio { width:100%; margin-top:0.8rem; border-radius:999px; }
  .url-box { background:#090614; border:1px solid rgba(0,240,255,0.35); padding:0.65rem; border-radius:10px; font-family:monospace; font-size:0.78rem; color:var(--cyan); word-break:break-all; margin-top:0.45rem; }
  .progress-wrap { width:100%; height:10px; background:#090614; border-radius:999px; overflow:hidden; margin-top:0.5rem; display:none; }
  .progress-bar { height:100%; width:0%; background:linear-gradient(90deg,var(--cyan),var(--pink)); transition:width 0.2s; }
</style>
</head>
<body>

<!-- PANTALLA DE ACCESO CON CONTRASEÑA -->
<div id="loginOverlay">
  <div class="login-box">
    <h1>MG BARCELONA LIVE</h1>
    <p style="font-size:0.88rem;color:rgba(255,255,255,0.72);margin-bottom:1.4rem;">Acceso Privado al Estudio del Servidor 24/7</p>
    <form onsubmit="doLogin(event)">
      <label style="font-size:0.8rem;display:block;text-align:left;margin-bottom:0.3rem;color:var(--gold);">👤 Usuario Administrador:</label>
      <input type="text" id="loginUser" value="moises" required>
      <label style="font-size:0.8rem;display:block;text-align:left;margin-bottom:0.3rem;color:var(--gold);">🔑 Contraseña del Servidor:</label>
      <input type="password" id="loginPass" placeholder="Introduce tu contraseña (mg2026)" required>
      <button type="submit" class="btn btn-primary" style="width:100%;padding:0.8rem;font-size:0.95rem;margin-top:0.4rem;">🔓 Entrar al Servidor</button>
    </form>
    <p id="loginErr" style="color:var(--pink);font-size:0.82rem;margin-top:0.8rem;"></p>
  </div>
</div>

<div class="wrap">
  <div class="header">
    <div>
      <div class="title">MG BARCELONA LIVE · ESTUDIO TOTAL EN EL SERVIDOR 24/7</div>
      <p style="font-size:0.82rem;color:rgba(255,255,255,0.7);">Radio 24h · Carpetas de Música · Presentador IA · Plantillas · Vídeos · Publicidad · Fotografías · Sponsors</p>
    </div>
    <div style="display:flex;gap:0.55rem;align-items:center;flex-wrap:wrap;">
      <button class="btn btn-gold" onclick="syncAllToWeb()">🚀 Actualizar Web de la Radio</button>
      <a class="btn" href="https://mgbarcelonalive.github.io/" target="_blank">🌐 Ver Web Pública</a>
      <button class="btn" onclick="logout()">🔒 Salir</button>
    </div>
  </div>

  <div id="statusBanner" style="margin-bottom:0.9rem;padding:0.65rem 1.1rem;border-radius:12px;background:rgba(0,240,255,0.08);border:1px solid rgba(0,240,255,0.3);font-size:0.84rem;color:var(--cyan);display:flex;justify-content:space-between;align-items:center;">
    <span id="globalMsg">✅ Conectado al Servidor MG Barcelona Live 24/7.</span>
    <span id="specMini" style="color:var(--gold);font-weight:700;"></span>
  </div>

  <!-- 9 PESTAÑAS COMPLETAS IGUAL QUE LA HERRAMIENTA DEL PC -->
  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('tab-musica', this)">📡 1. Emisión y Carpetas de Música</button>
    <button class="tab-btn" onclick="showTab('tab-cunas', this)">🎙️ 2. Presentador IA y Cuñas</button>
    <button class="tab-btn" onclick="showTab('tab-web', this)">🎨 3. Plantillas de la Web</button>
    <button class="tab-btn" onclick="showTab('tab-videos', this)">🎬 4. Vídeos Musicales (<span id="tabVidCount">0</span>)</button>
    <button class="tab-btn" onclick="showTab('tab-ads', this)">📣 5. Publicidad Radio (<span id="tabAdCount">0</span>)</button>
    <button class="tab-btn" onclick="showTab('tab-fotos', this)">📸 6. Fotografías Moisés (<span id="tabFotoCount">0</span>)</button>
    <button class="tab-btn" onclick="showTab('tab-fondos', this)">🌌 7. Fondos de Vídeo (<span id="tabBgCount">0</span>)</button>
    <button class="tab-btn" onclick="showTab('tab-sponsors', this)">🤝 8. Sponsors (<span id="tabSpCount">0</span>)</button>
    <button class="tab-btn" onclick="showTab('tab-specs', this)">⚙️ 9. Capacidad Técnica y Logs</button>
  </div>

  <!-- 1. EMISIÓN Y CARPETAS DE MÚSICA -->
  <div id="tab-musica" class="tab-panel active">
    <div class="grid">
      <div class="card">
        <h2>📡 Emisión 24/7 desde el Servidor</h2>
        <div class="stat-row"><span>Sonando ahora:</span><strong id="nowPlaying" style="color:var(--cyan);">Cargando...</strong></div>
        <div class="stat-row"><span>Modo:</span><strong>AutoDJ Servidor 24/7 (Sin Virtual DJ)</strong></div>
        <div class="stat-row"><span>Oyentes conectados:</span><strong id="listenersCount" style="color:var(--gold);">0</strong></div>
        <div style="margin-top:0.9rem;display:flex;gap:0.55rem;flex-wrap:wrap;">
          <button class="btn btn-primary" onclick="skipTrack()">⏭ Siguiente Canción</button>
          <a class="btn" href="/stream" target="_blank">🔗 Abrir Stream Directo</a>
        </div>
        <audio controls preload="none" src="/stream"></audio>
        <p style="font-size:0.75rem;color:rgba(255,255,255,0.5);margin-top:0.75rem;">URL fija de tu servidor:</p>
        <div class="url-box" id="streamUrlBox"></div>
      </div>

      <!-- SUBIR CARPETAS ENTERAS DE MÚSICA O ARCHIVOS SUELTOS -->
      <div class="card">
        <h2>📁 Subir Carpetas Llenas de Música o Archivos MP3</h2>
        <p style="font-size:0.8rem;color:rgba(255,255,255,0.68);margin-bottom:0.75rem;">
          Puedes elegir una <b>carpeta entera de tu disco</b> (subirá todos los MP3 de dentro automáticamente) o seleccionar canciones sueltas:
        </p>
        <div style="margin-bottom:0.85rem;padding:0.8rem;border-radius:12px;border:1px dashed var(--cyan);background:rgba(0,240,255,0.04);">
          <label style="font-size:0.82rem;font-weight:700;color:var(--cyan);display:block;margin-bottom:0.4rem;">📁 Opción A: Subir Carpeta Entera de Música</label>
          <input type="file" id="folderInput" webkitdirectory directory multiple onchange="uploadMusicBatch(this.files)">
        </div>
        <div style="padding:0.8rem;border-radius:12px;border:1px dashed var(--pink);background:rgba(255,45,120,0.04);">
          <label style="font-size:0.82rem;font-weight:700;color:var(--pink);display:block;margin-bottom:0.4rem;">🎵 Opción B: Subir Canciones MP3 Sueltas</label>
          <input type="file" id="filesInput" accept=".mp3" multiple onchange="uploadMusicBatch(this.files)">
        </div>
        <div class="progress-wrap" id="musicProgressWrap"><div class="progress-bar" id="musicProgressBar"></div></div>
        <p id="uploadStatus" style="font-size:0.82rem;margin-top:0.65rem;color:var(--gold);"></p>
      </div>

      <div class="card" style="grid-column: 1 / -1;">
        <h2>🎵 Biblioteca de Canciones en el Servidor (<span id="musicCount">0</span> temas)</h2>
        <div class="track-list" id="musicList"></div>
      </div>
    </div>
  </div>

  <!-- 2. PRESENTADOR VIRTUAL IA Y CUÑAS -->
  <div id="tab-cunas" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>🎙️ Configurar Presentador Virtual y Cuñas</h2>
        <p style="font-size:0.82rem;color:rgba(255,255,255,0.7);margin-bottom:0.8rem;">
          El servidor intercala automáticamente las cuñas oficiales entre las canciones:
        </p>
        <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Sonar 1 cuña automáticamente cada cuántas canciones:</label>
        <input type="number" id="cunaEveryN" value="3" min="1" max="20">
        <button class="btn btn-primary" onclick="saveCunaConfig()" style="width:100%;margin-bottom:1rem;">💾 Guardar Frecuencia de Cuñas</button>

        <h2 style="margin-top:0.5rem;">⬆️ Subir Nuevas Cuñas (.mp3)</h2>
        <input type="file" id="cunaInput" accept=".mp3" multiple onchange="uploadCunasBatch(this.files)">
        <p id="cunaUploadStatus" style="font-size:0.82rem;color:var(--gold);"></p>
      </div>

      <div class="card">
        <h2>🔊 Cuñas Activas en el Servidor (<span id="cunasCount">0</span>)</h2>
        <div class="track-list" id="cunasList"></div>
      </div>
    </div>
  </div>

  <!-- 3. PLANTILLAS DE LA WEB -->
  <div id="tab-web" class="tab-panel">
    <div class="grid">
      <div class="card" style="grid-column: 1 / -1;">
        <h2>🎨 Cambiar Diseño / Plantilla de la Web en Directo</h2>
        <p style="font-size:0.85rem;color:rgba(255,255,255,0.7);margin-bottom:0.6rem;">
          Plantilla activa en <code>mgbarcelonalive.github.io</code>: <strong id="currentTplLabel" style="color:var(--cyan);">principal</strong>
        </p>
        <div class="tpl-grid" id="tplGrid"></div>
      </div>

      <div class="card" style="grid-column: 1 / -1;">
        <h2>🔗 Conectar Stream Fijo del Servidor con la Web</h2>
        <div style="display:flex;gap:0.7rem;flex-wrap:wrap;">
          <input type="text" id="customStreamUrl" style="flex:1;min-width:260px;margin:0;">
          <button class="btn btn-primary" onclick="updateWebStreamUrl()">🌐 Publicar este Stream en la Web</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 4. VÍDEOS MUSICALES AUTOMÁTICOS -->
  <div id="tab-videos" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>🎬 Subir Vídeos Musicales (.mp4)</h2>
        <form onsubmit="uploadMediaFile(event, 'videos', 'webVideoFile', 'videoUploadStatus')">
          <input type="file" id="webVideoFile" accept=".mp4" multiple required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir Vídeo(s) MP4 y Actualizar Web</button>
        </form>
        <p id="videoUploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>
      <div class="card">
        <h2>📺 Vídeos Musicales en el Servidor (<span id="webVideosCount">0</span>)</h2>
        <div class="track-list" id="webVideosList"></div>
      </div>
    </div>
  </div>

  <!-- 5. PUBLICIDAD DE LA RADIO -->
  <div id="tab-ads" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>📣 Subir Anuncio de Publicidad (.mp4)</h2>
        <form onsubmit="uploadMediaFile(event, 'publicidad', 'webAdFile', 'adUploadStatus')">
          <input type="file" id="webAdFile" accept=".mp4" multiple required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir Anuncio(s) MP4 y Actualizar Web</button>
        </form>
        <p id="adUploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>
      <div class="card">
        <h2>📣 Anuncios Activos (<span id="webAdsCount">0</span>)</h2>
        <div class="track-list" id="webAdsList"></div>
      </div>
    </div>
  </div>

  <!-- 6. FOTOGRAFÍAS MOISÉS GALLARDO -->
  <div id="tab-fotos" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>📸 Subir Fotografías · Moisés Gallardo</h2>
        <form onsubmit="uploadWebPhoto(event)">
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Título / Evento:</label>
          <input type="text" id="photoTitle" placeholder="Ej: Saturgays Barcelona" required>
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Club / Sala:</label>
          <input type="text" id="photoClub" value="Barcelona Club" required>
          <label style="font-size:0.8rem;display:block;margin-bottom:0.3rem;">Plantilla:</label>
          <select id="photoTpl">
            <option value="principal">🏆 Plantilla Principal</option>
            <option value="todas">🌟 Todas las Plantillas</option>
          </select>
          <input type="file" id="webPhotoFile" accept=".jpg,.jpeg,.png,.webp" multiple required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir Fotografía(s) y Actualizar Web</button>
        </form>
        <p id="photoUploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>
      <div class="card" style="grid-column: span 2;">
        <h2>🖼️ Galería Fotográfica en el Servidor (<span id="photosCount">0</span> fotos)</h2>
        <div class="photo-grid" id="photosGrid"></div>
      </div>
    </div>
  </div>

  <!-- 7. VÍDEOS DE FONDO DE LAS PLANTILLAS -->
  <div id="tab-fondos" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>🌌 Subir Vídeo de Fondo de Pantalla (.mp4)</h2>
        <form onsubmit="uploadMediaFile(event, 'fondos', 'bgVideoFile', 'bgUploadStatus')">
          <input type="file" id="bgVideoFile" accept=".mp4" multiple required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir Fondo(s) MP4 y Actualizar Web</button>
        </form>
        <p id="bgUploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>
      <div class="card">
        <h2>🌌 Fondos de Pantalla Activos (<span id="bgVideosCount">0</span>)</h2>
        <div class="track-list" id="bgVideosList"></div>
      </div>
    </div>
  </div>

  <!-- 8. SPONSORS Y PATROCINADORES -->
  <div id="tab-sponsors" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>🤝 Subir Logo de Sponsor (.png / .jpg / .webp)</h2>
        <form onsubmit="uploadMediaFile(event, 'sponsors', 'sponsorFile', 'sponsorUploadStatus')">
          <input type="file" id="sponsorFile" accept=".png,.jpg,.jpeg,.webp" multiple required>
          <button type="submit" class="btn btn-primary" style="width:100%;">⬆️ Subir Sponsor y Actualizar Web</button>
        </form>
        <p id="sponsorUploadStatus" style="font-size:0.82rem;margin-top:0.75rem;color:var(--gold);"></p>
      </div>
      <div class="card">
        <h2>🤝 Sponsors en el Servidor (<span id="sponsorsCount">0</span>)</h2>
        <div class="track-list" id="sponsorsList"></div>
      </div>
    </div>
  </div>

  <!-- 9. CAPACIDAD TÉCNICA DEL SERVIDOR Y LOGS -->
  <div id="tab-specs" class="tab-panel">
    <div class="grid">
      <div class="card">
        <h2>⚙️ Ficha Técnica y Capacidad del Servidor</h2>
        <div class="stat-row"><span>Procesador (CPU):</span><strong id="specCpu" style="color:var(--cyan);">-</strong></div>
        <div class="stat-row"><span>Memoria RAM Total / Libre:</span><strong id="specRam" style="color:var(--gold);">-</strong></div>
        <div class="stat-row"><span>Almacenamiento en Disco:</span><strong id="specDisk" style="color:var(--cyan);">-</strong></div>
        <div class="stat-row"><span>Sistema / Arquitectura:</span><strong id="specArch">-</strong></div>
        <div class="stat-row"><span>Tiempo activo ininterrumpido:</span><strong id="specUptime">-</strong></div>
      </div>

      <div class="card">
        <h2>📋 Registro de Actividad del Servidor (Logs en Vivo)</h2>
        <div class="track-list" id="serverLogsBox" style="font-family:monospace;font-size:0.76rem;line-height:1.5;"></div>
      </div>
    </div>
  </div>
</div>

<script>
let SESSION_PASS = sessionStorage.getItem('mg_srv_pass') || '';
if (SESSION_PASS) {
  document.getElementById('loginOverlay').style.display = 'none';
}

document.getElementById('streamUrlBox').textContent = window.location.origin + '/stream';
document.getElementById('customStreamUrl').value = window.location.origin + '/stream';

async function doLogin(e) {
  e.preventDefault();
  const pw = document.getElementById('loginPass').value;
  const r = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: pw })
  });
  const res = await r.json();
  if (res.ok) {
    SESSION_PASS = pw;
    sessionStorage.setItem('mg_srv_pass', pw);
    document.getElementById('loginOverlay').style.display = 'none';
    refreshStatus();
  } else {
    document.getElementById('loginErr').textContent = '❌ Contraseña incorrecta. Por defecto es: mg2026';
  }
}

function logout() {
  SESSION_PASS = '';
  sessionStorage.removeItem('mg_srv_pass');
  document.getElementById('loginOverlay').style.display = 'flex';
}

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

    if (d.specs) {
      document.getElementById('specCpu').textContent = `${d.specs.cpu_cores} Núcleos vCPU dedicados`;
      document.getElementById('specRam').textContent = `${d.specs.ram_total_gb} GB Total (${d.specs.ram_free_gb} GB Libres)`;
      document.getElementById('specDisk').textContent = `${d.specs.disk_free_gb} GB Libres de ${d.specs.disk_total_gb} GB`;
      document.getElementById('specArch').textContent = d.specs.arch;
      document.getElementById('specUptime').textContent = `${d.specs.uptime_min} min en línea`;
      document.getElementById('specMini').textContent = `CPU: ${d.specs.cpu_cores} núcleos | RAM: ${d.specs.ram_total_gb} GB | Disco Libre: ${d.specs.disk_free_gb} GB`;
    }

    if (d.logs) {
      document.getElementById('serverLogsBox').innerHTML = d.logs.slice().reverse().map(l => `<div>${l}</div>`).join('');
    }

    document.getElementById('musicList').innerHTML = d.music.length ? d.music.map(m =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">🎵 ${m}</span><button class="btn" style="padding:0.25rem 0.6rem;font-size:0.75rem;" onclick="playSpecific('musica', '${m.replace(/'/g,"\\'")}')">▶ Poner</button></div>`
    ).join('') : '<p style="font-size:0.8rem;color:rgba(255,255,255,0.4);padding:0.5rem;">Usa los botones de arriba para subir carpetas enteras de música.</p>';

    document.getElementById('cunasList').innerHTML = d.cunas.map(c =>
      `<div class="track-item"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">🔊 ${c}</span><button class="btn" style="padding:0.25rem 0.6rem;font-size:0.75rem;" onclick="playSpecific('cunas', '${c.replace(/'/g,"\\'")}')">🔊 Lanzar</button></div>`
    ).join('');

    document.getElementById('tplGrid').innerHTML = (d.templates || []).map(t =>
      `<button class="tpl-btn ${t.id === d.current_template ? 'active' : ''}" onclick="setWebTemplate('${t.id}')">${t.label}</button>`
    ).join('');

    const vList = d.web_videos || [];
    const aList = d.web_ads || [];
    const bgList = d.bg_videos || [];
    const spList = d.sponsors || [];
    const pList = d.web_photos || [];

    document.getElementById('webVideosCount').textContent = vList.length;
    document.getElementById('tabVidCount').textContent = vList.length;
    document.getElementById('webAdsCount').textContent = aList.length;
    document.getElementById('tabAdCount').textContent = aList.length;
    document.getElementById('bgVideosCount').textContent = bgList.length;
    document.getElementById('tabBgCount').textContent = bgList.length;
    document.getElementById('sponsorsCount').textContent = spList.length;
    document.getElementById('tabSpCount').textContent = spList.length;
    document.getElementById('photosCount').textContent = pList.length;
    document.getElementById('tabFotoCount').textContent = pList.length;

    document.getElementById('webVideosList').innerHTML = vList.map((v, i) =>
      `<div class="track-item"><span>🎬 ${i+1}. ${v}</span><a class="btn" style="padding:0.2rem 0.55rem;font-size:0.73rem;" href="/${v}" target="_blank">▶ Ver</a></div>`
    ).join('');

    document.getElementById('webAdsList').innerHTML = aList.map((a, i) =>
      `<div class="track-item"><span>📣 ${i+1}. ${a.nombre || a.archivo}</span><a class="btn" style="padding:0.2rem 0.55rem;font-size:0.73rem;" href="/${a.archivo}" target="_blank">▶ Ver</a></div>`
    ).join('');

    document.getElementById('bgVideosList').innerHTML = bgList.map((b, i) =>
      `<div class="track-item"><span>🌌 ${i+1}. ${b}</span><a class="btn" style="padding:0.2rem 0.55rem;font-size:0.73rem;" href="/${b}" target="_blank">▶ Ver</a></div>`
    ).join('');

    document.getElementById('sponsorsList').innerHTML = spList.map((s, i) =>
      `<div class="track-item"><span>🤝 ${i+1}. ${s}</span><a class="btn" style="padding:0.2rem 0.55rem;font-size:0.73rem;" href="/${s}" target="_blank">👁️ Ver</a></div>`
    ).join('');

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

async function uploadMusicBatch(fileList) {
  const mp3s = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith('.mp3'));
  const status = document.getElementById('uploadStatus');
  const pWrap = document.getElementById('musicProgressWrap');
  const pBar = document.getElementById('musicProgressBar');
  if (!mp3s.length) {
    status.textContent = '⚠️ No se encontraron archivos .mp3 en la selección.';
    return;
  }
  pWrap.style.display = 'block';
  let subidos = 0;
  for (let i = 0; i < mp3s.length; i++) {
    const f = mp3s[i];
    const pct = Math.round(((i + 1) / mp3s.length) * 100);
    pBar.style.width = pct + '%';
    status.textContent = `Subiendo (${i+1}/${mp3s.length} · ${pct}%): ${f.name}...`;
    const r = await fetch(`/api/upload?type=musica&name=${encodeURIComponent(f.name)}`, {
      method: 'POST',
      headers: { 'X-Admin-Pass': SESSION_PASS },
      body: f
    });
    const res = await r.json();
    if (!res.ok) { status.textContent = res.message || 'Error'; return; }
    subidos++;
  }
  status.textContent = `✅ ¡Carpeta subida! ${subidos} canciones MP3 añadidas al servidor.`;
  refreshStatus();
}

async function uploadCunasBatch(fileList) {
  const mp3s = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith('.mp3'));
  const status = document.getElementById('cunaUploadStatus');
  let subidos = 0;
  for (let i = 0; i < mp3s.length; i++) {
    const f = mp3s[i];
    status.textContent = `Subiendo cuña (${i+1}/${mp3s.length}): ${f.name}...`;
    await fetch(`/api/upload?type=cunas&name=${encodeURIComponent(f.name)}`, {
      method: 'POST',
      headers: { 'X-Admin-Pass': SESSION_PASS },
      body: f
    });
    subidos++;
  }
  status.textContent = `✅ ${subidos} cuña(s) añadidas al servidor.`;
  refreshStatus();
}

async function saveCunaConfig() {
  const n = parseInt(document.getElementById('cunaEveryN').value || '3', 10);
  const r = await fetch('/api/cuna_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Pass': SESSION_PASS },
    body: JSON.stringify({ every_n: n })
  });
  const res = await r.json();
  setMsg(res.message || 'Configuración guardada');
}

async function setWebTemplate(tplId) {
  setMsg(`Activando plantilla "${tplId}" en la web...`);
  const r = await fetch('/api/set_template', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Pass': SESSION_PASS },
    body: JSON.stringify({ plantilla: tplId })
  });
  const res = await r.json();
  setMsg(res.message || '');
  refreshStatus();
}

async function updateWebStreamUrl() {
  const streamUrl = document.getElementById('customStreamUrl').value.trim();
  if (!streamUrl) return;
  setMsg('Publicando enlace del stream en la web...');
  const r = await fetch('/api/set_stream_url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Pass': SESSION_PASS },
    body: JSON.stringify({ stream_url: streamUrl })
  });
  const res = await r.json();
  setMsg(res.message || '');
}

async function uploadMediaFile(e, kind, inputId, statusId) {
  e.preventDefault();
  const status = document.getElementById(statusId);
  const files = document.getElementById(inputId).files;
  if (!files.length) return;
  let subidos = 0;
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    status.textContent = `Subiendo (${i+1}/${files.length}): ${f.name}...`;
    const r = await fetch(`/api/upload_web_video?kind=${encodeURIComponent(kind)}&name=${encodeURIComponent(f.name)}`, {
      method: 'POST',
      headers: { 'X-Admin-Pass': SESSION_PASS },
      body: f
    });
    const res = await r.json();
    if (!res.ok) { status.textContent = res.message || 'Error'; return; }
    subidos++;
  }
  status.textContent = `✅ ${subidos} archivo(s) subidos al servidor y actualizados en la web.`;
  document.getElementById(inputId).value = '';
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
  let subidas = 0;
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    status.textContent = `Subiendo foto (${i+1}/${files.length}): ${f.name}...`;
    const q = `name=${encodeURIComponent(f.name)}&title=${encodeURIComponent(title)}&club=${encodeURIComponent(club)}&tpl=${encodeURIComponent(tpl)}`;
    const r = await fetch(`/api/upload_web_photo?${q}`, {
      method: 'POST',
      headers: { 'X-Admin-Pass': SESSION_PASS },
      body: f
    });
    const res = await r.json();
    if (!res.ok) { status.textContent = res.message || 'Error'; return; }
    subidas++;
  }
  status.textContent = `✅ ${subidas} fotografía(s) añadidas al servidor y a la web`;
  document.getElementById('webPhotoFile').value = '';
  refreshStatus();
}

async function syncAllToWeb() {
  setMsg('🚀 Sincronizando todos los catálogos con la web pública mgbarcelonalive.github.io...');
  const r = await fetch('/api/sync_web', {
    method: 'POST',
    headers: { 'X-Admin-Pass': SESSION_PASS }
  });
  const res = await r.json();
  setMsg(res.message || '✅ Web actualizada');
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
                "bg_videos": ENGINE.list_bg_videos(),
                "sponsors": ENGINE.list_sponsors(),
                "specs": get_server_specs(),
                "logs": SERVER_LOGS[-40:],
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

        if path.startswith(("/videos/", "/publicidad/", "/eventos_fotos/", "/sponsors/")):
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
            self.send_response(302)
            self.send_header("Location", f"https://mgbarcelonalive.github.io/{rel}")
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/login":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if body.get("password") == ADMIN_PASS:
                add_log("Inicio de sesión de administrador correcto.")
                self._send_json(200, {"ok": True})
            else:
                self._send_json(403, {"ok": False})
            return

        if path == "/api/next":
            ENGINE.skip_requested = True
            add_log("Salto manual a la siguiente canción.")
            self._send_json(200, {"ok": True})
            return

        if path == "/api/cuna_config":
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            ENGINE.cuna_every_n = max(1, int(body.get("every_n", 3)))
            add_log(f"Frecuencia de cuñas ajustada a cada {ENGINE.cuna_every_n} canciones.")
            self._send_json(200, {"ok": True, "message": f"✅ Cuñas programadas cada {ENGINE.cuna_every_n} canciones"})
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
                add_log(f"Reproducción manual solicitada: {target.name}")
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

            add_log(f"Archivo de audio subido ({up_type}): {fname}")
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

            add_log(f"Plantilla web cambiada en directo a: {tpl}")
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
            add_log(f"URL del stream actualizada en la web: {new_url}")
            self._send_json(200, {"ok": True, "message": f"✅ Stream conectado en la web ({updated} plantillas actualizadas)"})
            return

        if path == "/api/upload_web_video":
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
                return
            qs = parse_qs(parsed.query)
            kind = qs.get("kind", ["videos"])[0]
            fname = Path(unquote(qs.get("name", ["video.mp4"])[0])).name
            length = int(self.headers.get("Content-Length", "0"))
            media_bytes = self.rfile.read(length)

            if kind == "publicidad":
                rel_path = f"publicidad/{fname}"
                (PUBLICIDAD_DIR / fname).write_bytes(media_bytes)
                if WEB_DIR.exists():
                    (WEB_DIR / "publicidad" / fname).write_bytes(media_bytes)
                github_put_file(rel_path, media_bytes, f"Subir anuncio {fname}")
                pub_info = load_json_manifest("publicidad.json", {"intervalo": 10, "anuncios": []})
                anuncios = pub_info.get("anuncios", [])
                if not any(a.get("archivo") == rel_path for a in anuncios):
                    anuncios.append({"archivo": rel_path, "tipo": "video", "nombre": fname})
                pub_info["anuncios"] = anuncios
                save_json_manifest("publicidad.json", pub_info, f"Añadir anuncio {fname}")
            elif kind == "fondos":
                rel_path = f"videos/fondos_principal/{fname}"
                (FONDOS_DIR / fname).write_bytes(media_bytes)
                if WEB_DIR.exists():
                    (WEB_DIR / "videos" / "fondos_principal").mkdir(parents=True, exist_ok=True)
                    (WEB_DIR / "videos" / "fondos_principal" / fname).write_bytes(media_bytes)
                github_put_file(rel_path, media_bytes, f"Subir fondo de plantilla {fname}")
            elif kind == "sponsors":
                rel_path = f"sponsors/{fname}"
                (SPONSORS_DIR / fname).write_bytes(media_bytes)
                if WEB_DIR.exists():
                    (WEB_DIR / "sponsors").mkdir(parents=True, exist_ok=True)
                    (WEB_DIR / "sponsors" / fname).write_bytes(media_bytes)
                github_put_file(rel_path, media_bytes, f"Subir sponsor {fname}")
            else:
                rel_path = f"videos/{fname}"
                (VIDEOS_DIR / fname).write_bytes(media_bytes)
                if WEB_DIR.exists():
                    (WEB_DIR / "videos" / fname).write_bytes(media_bytes)
                github_put_file(rel_path, media_bytes, f"Subir video musical {fname}")
                vids_info = load_json_manifest("videos.json", {"total": 0, "videos": []})
                vlist = vids_info.get("videos", [])
                if rel_path not in vlist:
                    vlist.append(rel_path)
                save_json_manifest("videos.json", {"total": len(vlist), "videos": vlist}, f"Añadir vídeo {fname}")

            add_log(f"Multimedia subido y publicado ({kind}): {fname}")
            self._send_json(200, {"ok": True, "message": f"✅ «{fname}» subido al servidor y publicado en la web"})
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

            add_log(f"Fotografía subida y publicada: {fname}")
            self._send_json(200, {"ok": True, "message": f"✅ Fotografía «{fname}» subida al servidor y publicada"})
            return

        if path == "/api/sync_web":
            pw = self.headers.get("X-Admin-Pass", "")
            if pw != ADMIN_PASS:
                self._send_json(403, {"ok": False, "message": "❌ Contraseña incorrecta"})
                return
            for manifest_name in ("videos.json", "publicidad.json", "eventos_fotos.json", "plantilla_live.json"):
                p = BASE_DIR / manifest_name
                if p.exists():
                    github_put_file(manifest_name, p.read_bytes(), f"Sincronizar {manifest_name} desde el servidor")
            add_log("Sincronización completa con la web pública realizada.")
            self._send_json(200, {"ok": True, "message": "✅ Web pública actualizada correctamente desde el servidor"})
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
