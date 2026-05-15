"""
Pont WebSocket JARVIS — Morphoz.io
Serveur WebSocket local (ws://localhost:8765) qui synchronise le pipeline vocal
avec le frontend Next.js en temps réel.

Messages Desktop → Frontend :
  {"type": "state",       "state":    "idle|listening|thinking|speaking"}
  {"type": "subtitle",    "text":     "Bonjour Harry..."}
  {"type": "voice_text",  "text":     "ce que l'utilisateur a dit"}
  {"type": "timer_start", "duration": 300, "label": "minuterie"}
  {"type": "timer_stop"}
  {"type": "globe",       "globe_action": "fly_to", "lat": 48.85, ...}
  {"type": "stats",       "cpu": 45.2, "ram": 62.1}

Messages Frontend → Desktop :
  {"type": "user_input", "text": "Quelle heure est-il ?"}
  {"type": "get_settings"}
  {"type": "ping"}
"""
import asyncio
import json
import logging
import os
import threading
from typing import Any, Callable, Optional, Set

log = logging.getLogger("ws_bridge")

# ── État global ────────────────────────────────────────────────────────────────
_clients:  Set[Any]                   = set()
_loop:     Optional[asyncio.AbstractEventLoop] = None
_thread:   Optional[threading.Thread] = None
_on_input: Optional[Callable[[str], None]] = None   # callback quand le frontend envoie du texte

_DESKTOP_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Handler WebSocket ──────────────────────────────────────────────────────────

async def _handler(ws):
    _clients.add(ws)
    log.info("[WsBridge] +1 client (%d connectés)", len(_clients))

    # Envoyer l'état courant au nouveau client
    await _safe_send(ws, {"type": "state", "state": "idle"})

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                msg_type = data.get("type", "")

                if msg_type == "user_input" and _on_input:
                    text = data.get("text", "").strip()
                    if text:
                        # Déclencher dans un thread séparé pour ne pas bloquer la loop asyncio
                        threading.Thread(
                            target=_on_input,
                            args=(text,),
                            daemon=True,
                            name="WsBridge-input",
                        ).start()

                elif msg_type == "get_settings":
                    cfg = _load_config()
                    await _safe_send(ws, {"type": "settings_data", "settings": cfg})

                elif msg_type == "ping":
                    await _safe_send(ws, {"type": "pong"})

            except json.JSONDecodeError:
                pass

    except Exception:
        pass
    finally:
        _clients.discard(ws)
        log.info("[WsBridge] -1 client (%d connectés)", len(_clients))


async def _safe_send(ws, payload: dict):
    try:
        await ws.send(json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass


async def _broadcast_async(msg: str):
    if not _clients:
        return
    dead = set()
    for ws in list(_clients):
        try:
            await ws.send(msg)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


# ── Serveur ────────────────────────────────────────────────────────────────────

async def _serve():
    try:
        import websockets
    except ImportError:
        log.error("[WsBridge] 'websockets' non installé — pip install websockets")
        return

    async with websockets.serve(_handler, "localhost", 8765, ping_interval=20, ping_timeout=10):
        log.info("[WsBridge] Serveur démarré sur ws://localhost:8765")
        await asyncio.Future()   # tourne indéfiniment


def _run_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(_serve())
    except Exception as e:
        log.error("[WsBridge] Loop terminée : %s", e)


# ── API publique ───────────────────────────────────────────────────────────────

def start(input_callback: Optional[Callable[[str], None]] = None):
    """Démarre le serveur WebSocket dans un thread daemon."""
    global _thread, _on_input
    _on_input = input_callback
    _thread = threading.Thread(target=_run_loop, daemon=True, name="WsBridge-Server")
    _thread.start()
    log.info("[WsBridge] Thread serveur lancé")


def broadcast(payload: dict[str, Any]):
    """Envoie un message JSON à tous les clients connectés. Thread-safe."""
    if not _loop or _loop.is_closed():
        return
    msg = json.dumps(payload, ensure_ascii=False)
    asyncio.run_coroutine_threadsafe(_broadcast_async(msg), _loop)


# ── Helpers sémantiques ────────────────────────────────────────────────────────

def send_state(state: str):
    """'idle' | 'listening' | 'thinking' | 'speaking'"""
    broadcast({"type": "state", "state": state})


def send_subtitle(text: str):
    """Texte de la réponse JARVIS pour le typewriter du frontend."""
    broadcast({"type": "subtitle", "text": text})


def send_voice_text(text: str):
    """Texte reconnu par STT — à afficher dans la zone de saisie."""
    broadcast({"type": "voice_text", "text": text})


def send_timer_start(seconds: int, label: str = "minuterie"):
    broadcast({"type": "timer_start", "duration": seconds, "label": label})


def send_timer_stop():
    broadcast({"type": "timer_stop"})


def send_globe(data: dict[str, Any]):
    """data doit contenir 'globe_action' + les coordonnées si besoin."""
    broadcast({"type": "globe", **data})


def send_stats(cpu: float, ram: float):
    broadcast({"type": "stats", "cpu": round(cpu, 1), "ram": round(ram, 1)})


# ── Utilitaire config ──────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        cfg_path = os.path.join(_DESKTOP_DIR, "jarvis_config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
