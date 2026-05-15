"""
Moniteur système JARVIS — Morphoz.io
Envoie CPU / RAM toutes les 5s au frontend via ws_bridge.
Démarre automatiquement avec le pipeline vocal.
"""
import threading
import time
import logging

log = logging.getLogger("stats_monitor")

_thread: threading.Thread | None = None
_running = False
INTERVAL = 5   # secondes


def _loop():
    try:
        import psutil
    except ImportError:
        log.warning("[Stats] psutil non installé — stats désactivées")
        return

    import ws_bridge as _ws

    global _running
    while _running:
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            _ws.send_stats(cpu, ram)
        except Exception as e:
            log.debug("[Stats] Erreur : %s", e)
        time.sleep(INTERVAL - 1)   # -1 car cpu_percent bloque 1s


def start():
    global _thread, _running
    if _thread and _thread.is_alive():
        return
    _running = True
    _thread = threading.Thread(target=_loop, daemon=True, name="StatsMonitor")
    _thread.start()
    log.info("[Stats] Moniteur CPU/RAM démarré (intervalle %ds)", INTERVAL)


def stop():
    global _running
    _running = False
