"""
Mode Iron Man — Morphoz.io
Détection de claps via PyAudio → bascule lumières Home Assistant.
Inspiré du mode clap de TechEnClair.

Usage:
    from iron_man import IronManMode
    mode = IronManMode(tts_speak=tts.speak)
    mode.start()   # démarre l'écoute
    mode.stop()    # arrête
"""
import threading
import time
import logging

log = logging.getLogger("iron_man")

# Seuil d'amplitude pour détecter un clap (valeur absolue int16)
CLAP_THRESHOLD = 8000
# Fenêtre de détection d'un double-clap (secondes)
DOUBLE_CLAP_WINDOW = 0.6
# Délai min entre deux claps d'un même double-clap
CLAP_MIN_GAP = 0.1

CHUNK = 1024
RATE  = 44100


class IronManMode:
    def __init__(self, tts_speak=None, ha_service=None):
        self._speak      = tts_speak or (lambda t: print(f"[iron_man] {t}"))
        self._ha         = ha_service
        self._active     = False
        self._lights_on  = True
        self._thread: threading.Thread | None = None
        self._last_clap  = 0.0
        self._clap_count = 0

    def start(self):
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="IronManMode",
        )
        self._thread.start()
        log.info("[IronMan] Mode activé — seuil=%d", CLAP_THRESHOLD)
        self._speak("Mode Iron Man activé, Harry. Deux claps pour basculer les lumières.")

    def stop(self):
        self._active = False
        log.info("[IronMan] Mode désactivé")
        self._speak("Mode Iron Man désactivé.")

    def _loop(self):
        try:
            import pyaudio
            import numpy as np
        except ImportError:
            log.warning("[IronMan] pyaudio ou numpy manquants — mode désactivé")
            return

        pa     = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
            while self._active:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    arr  = np.frombuffer(data, dtype=np.int16)
                    peak = int(np.abs(arr).max())

                    if peak > CLAP_THRESHOLD:
                        now = time.time()
                        gap = now - self._last_clap

                        if gap > CLAP_MIN_GAP:
                            self._last_clap  = now
                            self._clap_count += 1

                            if self._clap_count >= 2 and gap < DOUBLE_CLAP_WINDOW:
                                self._clap_count = 0
                                self._on_double_clap()
                            elif gap > DOUBLE_CLAP_WINDOW:
                                # Premier clap isolé → reset
                                self._clap_count = 1
                                self._last_clap  = now

                except Exception:
                    pass

        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            pa.terminate()

    def _on_double_clap(self):
        """Double clap détecté → bascule lumières HA."""
        self._lights_on = not self._lights_on
        etat = "on" if self._lights_on else "off"
        log.info("[IronMan] Double clap → lumières %s", etat)

        if self._ha:
            try:
                # Bascule toutes les lumières configurées
                self._ha.toggle_all_lights(etat)
            except Exception as e:
                log.debug("[IronMan] HA erreur : %s", e)
        else:
            # Fallback si ha_service pas injecté : essaie de l'importer
            try:
                from ha_service import traiter_commande_ha
                traiter_commande_ha(f"{'allume' if etat == 'on' else 'éteins'} toutes les lumières")
            except Exception as e:
                log.debug("[IronMan] ha_service fallback : %s", e)
