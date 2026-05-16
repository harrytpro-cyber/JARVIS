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

Messages Desktop → Frontend :
  {"type": "recipe",       "titre": "...", "ingredients": [...], "instructions": [...]}
  {"type": "notification", "title": "...", "body": "..."}
  {"type": "iron_man",     "etat": "on|off"}

Messages Frontend → Desktop :
  {"type": "user_input",  "text": "Quelle heure est-il ?"}
  {"type": "stop_audio"}
  {"type": "toggle_mic"}
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
_clients:       Set[Any]                   = set()
_loop:          Optional[asyncio.AbstractEventLoop] = None
_thread:        Optional[threading.Thread] = None
_on_input:      Optional[Callable[[str], None]] = None   # callback texte depuis frontend
_on_stop_audio: Optional[Callable[[], None]]    = None   # callback stop TTS
_on_toggle_mic: Optional[Callable[[], None]]    = None   # callback bascule micro

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

                elif msg_type == "update_settings":
                    new_cfg = data.get("settings", {})
                    if new_cfg:
                        _save_config(new_cfg)
                        await _safe_send(ws, {"type": "settings_saved", "ok": True})

                elif msg_type == "stop_audio":
                    if _on_stop_audio:
                        threading.Thread(target=_on_stop_audio, daemon=True).start()

                elif msg_type == "toggle_mic":
                    if _on_toggle_mic:
                        threading.Thread(target=_on_toggle_mic, daemon=True).start()

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

def start(
    input_callback:      Optional[Callable[[str], None]] = None,
    stop_audio_callback: Optional[Callable[[], None]]    = None,
    toggle_mic_callback: Optional[Callable[[], None]]    = None,
):
    """Démarre le serveur WebSocket dans un thread daemon."""
    global _thread, _on_input, _on_stop_audio, _on_toggle_mic
    _on_input      = input_callback
    _on_stop_audio = stop_audio_callback
    _on_toggle_mic = toggle_mic_callback
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


def send_recipe(titre: str, ingredients: list, instructions: list,
                portions: int | None = None, temps: str | None = None):
    """Affiche une recette dans le HUD frontend."""
    payload: dict = {
        "type":         "recipe",
        "titre":        titre,
        "ingredients":  ingredients,
        "instructions": instructions,
    }
    if portions: payload["portions"] = portions
    if temps:    payload["temps"]    = temps
    broadcast(payload)


def send_notification(title: str, body: str):
    """Notification push vers le frontend."""
    broadcast({"type": "notification", "title": title, "body": body})


def send_iron_man(etat: str):
    """Synchronise l'état du mode Iron Man avec le frontend."""
    broadcast({"type": "iron_man", "etat": etat})


# ── Utilitaire config ──────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        cfg_path = os.path.join(_DESKTOP_DIR, "jarvis_config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(new_cfg: dict) -> bool:
    """Fusionne new_cfg dans jarvis_config.json et sauvegarde."""
    try:
        cfg_path = os.path.join(_DESKTOP_DIR, "jarvis_config.json")
        # Charger l'existant pour ne pas écraser les commentaires ou clés inconnues
        current = _load_config()
        current.update(new_cfg)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        log.info("[WsBridge] jarvis_config.json sauvegardé")
        return True
    except Exception as e:
        log.error("[WsBridge] Erreur sauvegarde config : %s", e)
        return False
