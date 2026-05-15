"""
JARVIS Desktop — PyWebView (frameless) + pystray (tray) + OWW (wake word).
Point d'entrée unique : python desktop/app.py
"""
# ── Chargement du .env AVANT tout import qui lirait des variables d'env ──
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

import sys
import json
import threading
import time
import subprocess
import http.server
import socketserver

# ── Chemins ───────────────────────────────────────────────────────────
_HERE     = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.dirname(_HERE)
_FRONTEND = os.path.join(_ROOT, "frontend")

TITLE          = "J.A.R.V.I.S"
WIDTH, HEIGHT  = 1200, 800
BACKEND_HEALTH = "http://localhost:8000/health"
FRONTEND_PORT  = 3002
FRONTEND_URL   = f"http://localhost:{FRONTEND_PORT}/index.html"


# ── Serveur HTTP interne pour le frontend ─────────────────────────────

class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=_FRONTEND, **kwargs)
    def log_message(self, *_):
        pass


def _is_port_free(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _start_frontend_server():
    if not _is_port_free(FRONTEND_PORT):
        print(f"[http] Port {FRONTEND_PORT} déjà occupé — serveur frontend existant réutilisé.")
        return
    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("127.0.0.1", FRONTEND_PORT), _SilentHandler) as srv:
            print(f"[http] Serveur frontend démarré sur le port {FRONTEND_PORT}.")
            srv.serve_forever()
    except OSError as exc:
        print(f"[http] Impossible de démarrer le serveur frontend : {exc}")


# ── API Python exposée au frontend via window.pywebview.api ──────────

class JarvisApi:
    """
    Fonctions appelables depuis le JS avec window.pywebview.api.<méthode>().
    Permet de lancer des apps Windows, contrôler le volume, etc.
    sans passer par le backend HTTP.
    """

    # Lancement d'applications
    _APPS = {
        "chrome":   "start chrome",
        "firefox":  "start firefox",
        "vscode":   "code .",
        "taskmgr":  "taskmgr",
        "explorer": "explorer",
        "notepad":  "notepad",
        "calc":     "calc",
        "mode-boulot": None,  # géré en JS (focus + ferme distractions)
    }

    def launch_app(self, name: str) -> dict:
        """Lance une application Windows."""
        cmd = self._APPS.get(name.lower())
        if cmd is None and name.lower() == "mode-boulot":
            return {"ok": True, "message": "Mode Boulot activé"}
        if cmd:
            subprocess.Popen(cmd, shell=True)
            return {"ok": True, "message": f"{name} lancé"}
        return {"ok": False, "error": f"Application inconnue : {name}"}

    def set_volume(self, direction: str) -> dict:
        """Monte ou baisse le volume système (nécessite nircmd ou powershell)."""
        try:
            # Méthode PowerShell native — fonctionne sans logiciel tiers
            if direction == "up":
                script = "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"
            else:
                script = "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", script],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def screenshot(self) -> dict:
        """Lance l'outil Capture Windows."""
        subprocess.Popen("snippingtool /clip", shell=True)
        return {"ok": True, "message": "Capture d'écran lancée"}


# ── Splash screen HTML ────────────────────────────────────────────────

SPLASH_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"/>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#020d1a;display:flex;flex-direction:column;
  align-items:center;justify-content:center;height:100vh;
  font-family:"Courier New",monospace;color:#00d4ff;
  overflow:hidden;user-select:none;-webkit-app-region:drag
}
canvas{position:fixed;top:0;left:0;pointer-events:none}
.ui{position:relative;z-index:10;text-align:center}
h1{font-size:42px;letter-spacing:.5em;margin-bottom:14px;
   text-shadow:0 0 24px #00d4ff55}
#status{font-size:11px;letter-spacing:.25em;color:#00d4ff66;min-height:16px;text-transform:uppercase}
.bar-bg{width:240px;height:1px;background:#0a2040;margin:20px auto 0;overflow:hidden}
.bar-fill{height:100%;background:#00d4ff;width:0%;transition:width .45s}
</style>
</head><body>
<canvas id="c"></canvas>
<div class="ui">
  <h1>J.A.R.V.I.S</h1>
  <div id="status">Initializing...</div>
  <div class="bar-bg"><div class="bar-fill" id="bar"></div></div>
</div>
<script>
const c=document.getElementById('c'),ctx=c.getContext('2d');
function resize(){c.width=innerWidth;c.height=innerHeight}resize();
addEventListener('resize',resize);
let ang=0;
(function frame(){
  ctx.clearRect(0,0,c.width,c.height);
  const cx=c.width/2,cy=c.height/2;
  [170,130,90,58,32].forEach((r,i)=>{
    ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);
    ctx.strokeStyle=`rgba(0,212,255,${.04+i*.022})`;
    ctx.lineWidth=1;ctx.stroke();
  });
  ctx.save();ctx.translate(cx,cy);ctx.rotate(ang);
  const g=ctx.createLinearGradient(0,-170,0,0);
  g.addColorStop(0,'rgba(0,212,255,0)');
  g.addColorStop(1,'rgba(0,212,255,.13)');
  ctx.beginPath();ctx.moveTo(0,0);
  ctx.arc(0,0,170,-Math.PI/2,-Math.PI/2+Math.PI/2.5);
  ctx.closePath();ctx.fillStyle=g;ctx.fill();ctx.restore();
  ang+=.018;requestAnimationFrame(frame);
})();
const steps=[
  [12,"Systems check..."],
  [28,"Loading core modules..."],
  [45,"Connecting to backend..."],
  [62,"Initializing LLM router..."],
  [78,"Starting memory systems..."],
  [92,"Loading interface..."],
  [100,"Ready."]
];
let si=0;
(function next(){
  if(si>=steps.length)return;
  const[p,m]=steps[si++];
  document.getElementById('bar').style.width=p+'%';
  document.getElementById('status').textContent=m;
  if(si<steps.length)setTimeout(next,520);
})();
</script>
</body></html>"""


# ── Application principale ────────────────────────────────────────────

class JarvisDesktop:
    def __init__(self):
        self.window           = None
        self.tray             = None
        self._api             = JarvisApi()
        self._pipeline        = None
        self._pipeline_started = False

    # ── Icône tray + ICO Windows ─────────────────────────────────────
    def _make_pil_icon(self):
        from PIL import Image, ImageDraw
        img  = Image.new("RGBA", (64, 64), (2, 13, 26, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse([ 3,  3, 61, 61], outline=(0, 212, 255, 255), width=2)
        draw.ellipse([13, 13, 51, 51], outline=(0, 212, 255, 150), width=1)
        draw.ellipse([25, 25, 39, 39], fill=(0, 212, 255, 255))
        assets = os.path.join(_HERE, "assets")
        os.makedirs(assets, exist_ok=True)
        img.save(os.path.join(assets, "jarvis.ico"), format="ICO")
        return img

    def _setup_tray(self):
        import pystray
        ico = self._make_pil_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Ouvrir JARVIS", self._show, default=True),
            pystray.MenuItem("Quitter",       self._quit),
        )
        self.tray = pystray.Icon("JARVIS", ico, "J.A.R.V.I.S", menu)
        self.tray.run_detached()

    def _show(self, *_):
        if self.window:
            self.window.show()
            self.window.restore()

    def _quit(self, *_):
        if self.tray:   self.tray.stop()
        if self.window: self.window.destroy()

    # ── Démarrage du pipeline vocal (différé après chargement UI) ────
    def _start_voice_pipeline(self):
        if self._pipeline_started:
            return
        self._pipeline_started = True
        print("[voice] Attente de la fenêtre principale (5 s)...")
        time.sleep(5)
        try:
            if _HERE not in sys.path:
                sys.path.insert(0, _HERE)
            from tts_service    import TTSService
            from voice_pipeline import VoicePipeline
            tts = TTSService()
            tts.speak("Bonjour, je suis JARVIS, votre assistant personnel. Systèmes en ligne.")
            self._pipeline = VoicePipeline(lambda: self.window, tts)
            self._pipeline.start()
        except Exception as exc:
            print(f"[voice] Erreur d'initialisation du pipeline : {exc}")

    # ── Attente backend ──────────────────────────────────────────────
    def _wait_backend(self, timeout: int = 30) -> bool:
        import urllib.request
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                urllib.request.urlopen(BACKEND_HEALTH, timeout=1)
                return True
            except Exception:
                time.sleep(1)
        return False

    # ── Chargement après splash ──────────────────────────────────────
    def _load_after_splash(self):
        ready = self._wait_backend()
        if not ready:
            print("[app] Backend injoignable — chargement en mode démo")
        self.window.load_url(FRONTEND_URL)

    # ── Point d'entrée ───────────────────────────────────────────────
    def run(self):
        import webview

        # 1. Serveur frontend
        threading.Thread(target=_start_frontend_server, daemon=True).start()
        time.sleep(0.4)

        # 2. Tray
        self._setup_tray()

        # 3. Fenêtre PyWebView
        self.window = webview.create_window(
            title     = TITLE,
            html      = SPLASH_HTML,
            width     = WIDTH,
            height    = HEIGHT,
            frameless = True,
            easy_drag = True,
            min_size  = (800, 600),
            js_api    = self._api,
        )

        def on_loaded():
            # 4. Chargement du frontend après le splash
            threading.Thread(target=self._load_after_splash, daemon=True).start()
            # 5. Pipeline vocal démarré APRÈS chargement (délai 5 s interne)
            threading.Thread(target=self._start_voice_pipeline, daemon=True).start()

        self.window.events.loaded += on_loaded
        webview.start(debug=False)


# ── Diagnostic des clés API au démarrage ─────────────────────────────

def _print_key_status():
    keys = [
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "GOOGLE_CLIENT_ID",
        "SPOTIFY_CLIENT_ID",
        "PORCUPINE_ACCESS_KEY",
        "ENCRYPTION_KEY",
        "JWT_SECRET_KEY",
    ]
    print("")
    print("  ─── Statut des clés API ───────────────────────")
    for key in keys:
        val = os.getenv(key, "")
        if val and val.strip():
            preview = val[:6] + "..." if len(val) > 6 else val
            print(f"  ✅  {key:<28} ({preview})")
        else:
            print(f"  ❌  {key:<28} manquante")
    print("  ────────────────────────────────────────────────")
    print("")


if __name__ == "__main__":
    _print_key_status()
    JarvisDesktop().run()
