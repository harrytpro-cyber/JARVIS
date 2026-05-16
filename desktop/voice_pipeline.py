"""
Pipeline vocal JARVIS — Morphoz.io
Architecture :
  VEILLE  → OpenWakeWord écoute sur stream PyAudio dédié
  ÉCOUTE  → stream fermé, sr.Microphone() ouvert 5 s max
  TRAITEMENT → local_resolver → intents → LLM backend
  RETOUR  → stream rouvert, silence = aucun message
"""
import asyncio
import json
import re
import threading
import time
import urllib.parse
import webbrowser
import subprocess
import os

import numpy as np
import pyaudio
import requests

# ── Pont WebSocket (frontend sync) ────────────────────────────────────────────
try:
    import ws_bridge as _ws
    _WS_OK = True
except ImportError:
    _WS_OK = False
    class _ws:                          # type: ignore[no-redef]
        """Stub silencieux si websockets n'est pas installé."""
        @staticmethod
        def start(**_): pass
        @staticmethod
        def send_state(_): pass
        @staticmethod
        def send_subtitle(_): pass
        @staticmethod
        def send_voice_text(_): pass
        @staticmethod
        def send_timer_start(s, l=""): pass
        @staticmethod
        def send_timer_stop(): pass
        @staticmethod
        def send_globe(_): pass

# ── Constantes ────────────────────────────────────────────────────────────────
CHUNK   = 1280
RATE    = 16000
BACKEND = "http://localhost:8000"

_DESKTOP_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Résolveur local (sans LLM) ────────────────────────────────────────────────
try:
    import sys as _sys
    if _DESKTOP_DIR not in _sys.path:
        _sys.path.insert(0, _DESKTOP_DIR)
    import local_resolver
    _LOCAL_RESOLVER_OK = True
except Exception as _e:
    print(f"[voice] local_resolver non chargé ({_e})")
    _LOCAL_RESOLVER_OK = False

# ── AppLauncher ───────────────────────────────────────────────────────────────
try:
    from app_launcher import AppLauncher
except Exception as _e:
    print(f"[voice] app_launcher non chargé ({_e}) — fallback basique")

    class AppLauncher:                                          # type: ignore[no-redef]
        def launch(self, text: str) -> str | None:
            t = text.lower()
            basic = {
                "chrome":       r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                "notepad":      "notepad.exe",
                "calculatrice": "calc.exe",
                "explorateur":  "explorer.exe",
            }
            for key, path in basic.items():
                if key in t:
                    try:
                        subprocess.Popen(path, shell=True)
                        return f"Je lance {key}."
                    except Exception:
                        return f"Impossible de lancer {key}."
            return None

        def close(self, text: str) -> str | None:
            return None


# ── Config ────────────────────────────────────────────────────────────────────

def _charger_config() -> dict:
    try:
        cfg_path = os.path.join(_DESKTOP_DIR, "jarvis_config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ── Détection d'intention ─────────────────────────────────────────────────────

def detect_intent(text: str) -> str:
    """
    Ordre de priorité : du plus spécifique au plus général.
    Les résolutions locales (maths, minuteries, blagues…) s'appliquent
    AVANT cette fonction — elle n'est atteinte que si local_resolver retourne None.
    """
    t = text.lower()

    # Google Docs
    if any(w in t for w in ["google doc", "google drive", "crée un document",
                             "créer un document", "ouvre un doc", "modifie le document",
                             "écris dans le document", "ajoute dans le doc"]):
        return "google_docs"

    # Google Calendar
    if any(w in t for w in ["agenda", "calendrier", "mes événements", "mes rendez-vous",
                             "prochain rendez-vous", "google calendar",
                             "crée un événement", "ajoute un rendez-vous"]):
        return "google_calendar"

    # Google Sheets
    if any(w in t for w in ["google sheets", "feuille de calcul", "crée un tableau google",
                             "crée une feuille", "ouvre sheets"]):
        return "google_sheets"

    # Lecture email (distinct de write_email)
    if any(w in t for w in ["lis mes emails", "lis mes mails", "consulte mes emails",
                             "mes derniers emails", "mes derniers mails",
                             "vérifier mes mails", "nouveaux emails"]):
        return "read_email"

    # Rédaction email
    if any(w in t for w in ["envoie un email", "envoie un mail", "rédige un mail",
                             "écris un mail", "envoie un message à"]):
        return "write_email"

    # Musique Deezer
    if "deezer" in t:
        return "music_deezer"

    # Musique Spotify / musique générale
    if any(w in t for w in ["spotify", "musique", "chanson", "mets du", "joue", "play", "écouter"]):
        return "music"

    # Météo
    if any(w in t for w in ["météo", "quel temps", "alerte météo", "température extérieure"]):
        return "weather"

    # Sports
    if any(w in t for w in ["football", "foot", "score", "match", "résultat",
                             "classement", "ligue", "équipe"]):
        return "sport"

    # Home Assistant
    if any(w in t for w in ["lumière", "allume", "éteins la lumière", "thermostat",
                             "chauffage", "prise connectée", "home assistant", "domotique"]):
        return "home"

    # Vision écran
    if any(w in t for w in ["clique sur", "regarde l'écran", "qu'est-ce qui est affiché",
                             "analyse l'écran", "vision", "prends une capture"]):
        return "vision"

    # Caméra
    if any(w in t for w in ["regarde la caméra", "regarde avec ta caméra",
                             "active la caméra", "analyse la caméra"]):
        return "camera"

    # Mode Iron Man — détection de claps
    if any(w in t for w in ["mode iron man", "iron man", "détection de clap",
                             "active les claps", "mode clap"]):
        return "iron_man"

    # Dictée — tape du texte à la position du curseur
    if any(w in t for w in ["tape ", "dicte ", "dictée "]):
        return "dictee"

    # Fichiers / dossiers — avant "ouvre" pour éviter faux positifs
    if any(w in t for w in ["dossier", "fichier", "trie", "classe les",
                             "mes documents", "mes téléchargements", "explore"]):
        return "file"

    # Mode boulot
    if any(w in t for w in ["mode boulot", "mode travail", "espace de travail"]):
        return "mode_boulot"

    # YouTube
    if "youtube" in t:
        return "youtube"

    # Fermer une app
    if any(w in t for w in ["ferme", "quitte", "tue"]):
        return "close_app"

    # "arrête" uniquement si pas une minuterie ou volume
    if "arrête" in t and not any(w in t for w in ["minuteur", "minuterie", "timer",
                                                    "son", "volume"]):
        return "close_app"

    # Tâches / notes / courses — interceptés par local_resolver en priorité
    if any(w in t for w in ["tâche", "rappelle-moi", "rappelle moi", "note ça",
                             "prends note", "mes notes", "todo", "to-do",
                             "liste de courses", "mes courses"]):
        return "task"

    # Lancer une app
    if any(w in t for w in ["ouvre", "lance", "démarre", "start", "lancer", "exécute"]):
        return "launch_app"

    return "chat"


# ── Flow email multi-tours ────────────────────────────────────────────────────

class EmailFlow:
    _STEPS = [
        ("À qui voulez-vous envoyer ce mail ?", "recipient"),
        ("Quel est le sujet ?",                  "subject"),
        ("Que voulez-vous dire ?",               "body"),
    ]

    def __init__(self, tts_speak):
        self._speak = tts_speak
        self._data  = {}
        self._step  = 0
        self.active = False
        self._mode  = "gmail_web"   # "gmail_web" | "gmail_api"

    def start(self, mode: str = "gmail_web"):
        self.active  = True
        self._data   = {}
        self._step   = 0
        self._mode   = mode
        self._speak(self._STEPS[0][0])

    def handle(self, text: str) -> bool:
        _, field = self._STEPS[self._step]
        self._data[field] = text
        self._step += 1
        if self._step < len(self._STEPS):
            self._speak(self._STEPS[self._step][0])
            return False
        self._envoyer()
        self.active = False
        return True

    def _envoyer(self):
        r = self._data.get("recipient", "")
        s = self._data.get("subject",   "")
        b = self._data.get("body",      "")
        if self._mode == "gmail_api":
            try:
                from google_services import envoyer_email
                result = envoyer_email(r, s, b)
                self._speak(result)
                return
            except Exception as e:
                print(f"[email] API Gmail : {e}")
        # Fallback : ouvrir Gmail dans le navigateur
        url = (
            "https://mail.google.com/mail/?view=cm"
            f"&to={urllib.parse.quote(r)}"
            f"&su={urllib.parse.quote(s)}"
            f"&body={urllib.parse.quote(b)}"
        )
        webbrowser.open(url)
        self._speak("Votre mail est prêt dans Gmail. Vérifiez et envoyez quand vous voulez, Harry.")


# ── Flow création événement Calendar multi-tours ──────────────────────────────

class CalendarFlow:
    _STEPS = [
        ("Quel est le titre de l'événement ?",       "titre"),
        ("À quelle date ? (ex: demain, lundi 14h)",  "date_texte"),
        ("Quelle est la durée ? (ex: 1 heure)",      "duree"),
    ]

    def __init__(self, tts_speak):
        self._speak = tts_speak
        self._data  = {}
        self._step  = 0
        self.active = False

    def start(self):
        self.active = True
        self._data  = {}
        self._step  = 0
        self._speak(self._STEPS[0][0])

    def handle(self, text: str) -> bool:
        _, field = self._STEPS[self._step]
        self._data[field] = text
        self._step += 1
        if self._step < len(self._STEPS):
            self._speak(self._STEPS[self._step][0])
            return False
        self._creer()
        self.active = False
        return True

    def _creer(self):
        # Ouvre Google Calendar avec les infos pré-remplies si possible
        titre     = self._data.get("titre", "Événement")
        date_str  = self._data.get("date_texte", "")
        webbrowser.open("https://calendar.google.com/calendar/r/eventedit"
                        f"?text={urllib.parse.quote(titre)}")
        self._speak(
            f"J'ouvre Google Calendar avec le titre '{titre}'. "
            f"Complétez la date '{date_str}' et confirmez, Harry."
        )


# ── Pipeline vocal ────────────────────────────────────────────────────────────

class VoicePipeline:
    def __init__(self, window_ref, tts):
        self._win  = window_ref
        self._tts  = tts

        # Wrap speak pour broadcaster subtitle + state au frontend
        _real_speak = tts.speak
        def _bridged_speak(text: str):
            _ws.send_state("speaking")
            _ws.send_subtitle(text)
            _real_speak(text)
            # Petit délai puis retour idle (couvert par le _busy flag côté pipeline)
        tts.speak = _bridged_speak

        self._launcher       = AppLauncher()
        self._email_flow     = EmailFlow(tts.speak)
        self._calendar_flow  = CalendarFlow(tts.speak)
        self._pa             = None
        self._stream         = None
        self._model          = None
        self._model_name     = None
        self._busy           = False
        self._cfg            = _charger_config()

        if _LOCAL_RESOLVER_OK:
            local_resolver.init(tts.speak)

        # Démarrer le pont WebSocket (desktop → frontend)
        _ws.start(
            input_callback=self._handle_command,
            stop_audio_callback=self._stop_audio,
            toggle_mic_callback=self._toggle_mic,
        )

        # Moniteur CPU/RAM → frontend via ws_bridge
        try:
            import stats_monitor
            stats_monitor.start()
        except Exception as _e:
            print(f"[voice] stats_monitor non chargé ({_e})")

        # Mode Iron Man (optionnel)
        self._iron_man = None
        try:
            from iron_man import IronManMode
            self._iron_man = IronManMode(tts_speak=tts.speak)
        except Exception as _e:
            print(f"[voice] iron_man non chargé ({_e})")

        # Flag micro activé/désactivé
        self._mic_enabled = True

    # ── Démarrage ─────────────────────────────────────────────────────────────

    def start(self):
        threading.Thread(target=self._init_and_run, daemon=True).start()

    def _init_and_run(self):
        try:
            from wake_word_oww import _load_model
            self._model, self._model_name = _load_model()
        except Exception as exc:
            print(f"[voice] Impossible de charger OWW : {exc}")
            return
        self._open_oww_stream()
        print(f"[voice] Veille active — wake word : {self._model_name}")
        self._loop()

    def _open_oww_stream(self):
        if self._pa is None:
            self._pa = pyaudio.PyAudio()
        mic_idx = self._cfg.get("mic_device_index")
        kwargs  = {"input_device_index": int(mic_idx)} if mic_idx is not None else {}
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            **kwargs,
        )

    def _close_oww_stream(self):
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
        except Exception:
            pass

    # ── Boucle veille ─────────────────────────────────────────────────────────

    def _loop(self):
        while True:
            if self._tts.is_speaking or self._busy:
                time.sleep(0.05)
                continue
            if self._stream is None:
                try:
                    self._open_oww_stream()
                except Exception:
                    time.sleep(1)
                    continue
            try:
                raw = self._stream.read(CHUNK, exception_on_overflow=False)
            except Exception:
                continue
            arr   = np.frombuffer(raw, dtype=np.int16)
            pred  = self._model.predict(arr)
            score = pred.get(self._model_name, 0)
            if score > 0.5 and not self._busy:
                print(f"[voice] Wake word détecté — score {score:.2f}")
                self._busy = True
                threading.Thread(target=self._on_wake_sequence, daemon=True).start()

    # ── Séquence post-wake ────────────────────────────────────────────────────

    def _on_wake_sequence(self):
        try:
            # ── Écoute ────────────────────────────────────────────────────────
            _ws.send_state("listening")
            self._signal_listening()
            self._close_oww_stream()
            time.sleep(0.1)
            text = self._listen_for_command(timeout=5)

            if text:
                print(f"[STT] '{text}'")
                _ws.send_voice_text(text)    # affiche dans le frontend ce qui a été dit
                self._inject_ui(text)

                # ── Traitement ────────────────────────────────────────────────
                _ws.send_state("thinking")
                self._handle_command(text)   # _bridged_speak gère "speaking" + subtitle
            else:
                print("[voice] Rien détecté — retour veille silencieux")
        finally:
            try:
                self._open_oww_stream()
            except Exception as exc:
                print(f"[voice] Impossible de rouvrir le stream : {exc}")
            _ws.send_state("idle")
            self._busy = False

    # ── STT ───────────────────────────────────────────────────────────────────

    def _listen_for_command(self, timeout: int = 5) -> str | None:
        import speech_recognition as sr
        r       = sr.Recognizer()
        mic_idx = self._cfg.get("mic_device_index")
        try:
            mic_kwargs = {"device_index": int(mic_idx)} if mic_idx is not None else {}
            with sr.Microphone(sample_rate=RATE, **mic_kwargs) as source:
                r.adjust_for_ambient_noise(source, duration=0.4)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=10)
            text = r.recognize_google(audio, language="fr-FR")
            return text.strip() if text and len(text.strip()) > 2 else None
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as exc:
            print(f"[STT] Erreur : {exc}")
            return None

    # ── Traitement ────────────────────────────────────────────────────────────

    def _handle_command(self, text: str):
        # Flows multi-tours actifs
        if self._email_flow.active:
            self._email_flow.handle(text)
            return
        if self._calendar_flow.active:
            self._calendar_flow.handle(text)
            return

        # ── Résolution locale (sans LLM) ──────────────────────────────────────
        if _LOCAL_RESOLVER_OK:
            local_reply = self._resolve_locally(text)
            if local_reply:
                self._tts.speak(local_reply)
                return

        intent = detect_intent(text)
        print(f"[intent] {intent} — '{text}'")

        # ── Google Docs ───────────────────────────────────────────────────────
        if intent == "google_docs":
            self._handle_google_docs(text)
            return

        # ── Google Calendar ───────────────────────────────────────────────────
        if intent == "google_calendar":
            self._handle_google_calendar(text)
            return

        # ── Google Sheets ─────────────────────────────────────────────────────
        if intent == "google_sheets":
            self._handle_google_sheets(text)
            return

        # ── Lecture emails ────────────────────────────────────────────────────
        if intent == "read_email":
            threading.Thread(target=self._handle_read_email, daemon=True).start()
            return

        # ── Rédaction email ───────────────────────────────────────────────────
        if intent == "write_email":
            from google_services import google_disponible
            mode = "gmail_api" if google_disponible() else "gmail_web"
            self._email_flow.start(mode=mode)
            return

        # ── Lancer une application ────────────────────────────────────────────
        if intent == "launch_app":
            result = self._launcher.launch(text)
            if result:
                self._tts.speak(result)
            return

        # ── Fermer une application ────────────────────────────────────────────
        if intent == "close_app":
            result = self._launcher.close(text)
            if result:
                self._tts.speak(result)
            return

        # ── Mode boulot ───────────────────────────────────────────────────────
        if intent == "mode_boulot":
            threading.Thread(
                target=lambda: asyncio.run(self._run_mode_boulot()),
                daemon=True,
            ).start()
            return

        # ── Musique Spotify ───────────────────────────────────────────────────
        if intent == "music":
            self._handle_spotify(text)
            return

        # ── Musique Deezer ────────────────────────────────────────────────────
        if intent == "music_deezer":
            self._handle_deezer(text)
            return

        # ── Météo ─────────────────────────────────────────────────────────────
        if intent == "weather":
            try:
                from ha_service import get_meteo_actuelle
                self._tts.speak(get_meteo_actuelle())
                return
            except Exception as e:
                print(f"[voice] Météo : {e}")

        # ── Sports ────────────────────────────────────────────────────────────
        if intent == "sport":
            try:
                from sports_service import traiter_commande_sport
                result = traiter_commande_sport(text)
                if result:
                    self._tts.speak(result)
                    return
            except Exception as e:
                print(f"[voice] Sport : {e}")

        # ── Home Assistant ────────────────────────────────────────────────────
        if intent == "home":
            try:
                from ha_service import traiter_commande_ha
                result = traiter_commande_ha(text)
                if result:
                    self._tts.speak(result)
                    return
            except Exception as e:
                print(f"[voice] Home Assistant : {e}")

        # ── Fichiers / dossiers ───────────────────────────────────────────────
        if intent == "file":
            self._handle_file(text)
            return

        # ── Vision écran ──────────────────────────────────────────────────────
        if intent == "vision":
            threading.Thread(
                target=lambda: asyncio.run(self._run_vision(text)),
                daemon=True,
            ).start()
            return

        # ── Caméra ────────────────────────────────────────────────────────────
        if intent == "camera":
            threading.Thread(
                target=lambda: asyncio.run(self._run_camera(text)),
                daemon=True,
            ).start()
            return

        # ── Mode Iron Man ─────────────────────────────────────────────────────
        if intent == "iron_man":
            self._handle_iron_man(text)
            return

        # ── Dictée ────────────────────────────────────────────────────────────
        if intent == "dictee":
            self._handle_dictee(text)
            return

        # ── YouTube ───────────────────────────────────────────────────────────
        if intent == "youtube":
            if _LOCAL_RESOLVER_OK:
                result = local_resolver._chercher_youtube(text.lower())
                if result:
                    self._tts.speak(result)
            return

        # ── Tâches / notes / courses (local_resolver en priorité) ─────────────
        if intent == "task":
            if _LOCAL_RESOLVER_OK:
                result = local_resolver.resoudre_extras_locaux(text)
                if result:
                    self._tts.speak(result)
                    return

        # ── Fallback LLM ──────────────────────────────────────────────────────
        response = self._call_backend(text)
        if response:
            self._tts.speak(response)

    # ── Résolution locale ─────────────────────────────────────────────────────

    def _resolve_locally(self, text: str) -> str | None:
        try:
            return local_resolver.resoudre_tout(text)
        except Exception as e:
            print(f"[voice] local_resolver : {e}")
            return None

    # ── Handlers spécialisés ──────────────────────────────────────────────────

    def _handle_spotify(self, text: str):
        t = text.lower()

        # Lien musical personnalisé ("ma musique", "ma playlist")
        if any(w in t for w in ["ma musique", "ma playlist", "mets de la musique"]):
            musique_lien = self._cfg.get("musique_lien", "").strip()
            if musique_lien:
                webbrowser.open(musique_lien)
                self._tts.speak("C'est parti Harry, je lance votre musique.")
                return

        try:
            from spotify_controller import (spotify_rechercher, spotify_lecture_pause,
                                             spotify_suivant, spotify_precedent, spotify_stop)
            if any(w in t for w in ["pause", "stop", "arrête la musique"]):
                asyncio.run(spotify_stop())
                return
            if any(w in t for w in ["suivant", "prochain", "next"]):
                asyncio.run(spotify_suivant())
                return
            if any(w in t for w in ["précédent", "reviens", "previous"]):
                asyncio.run(spotify_precedent())
                return
            query = re.sub(
                r"\b(mets|joue|lance|play|écouter?|spotify|musique|chanson|sur spotify)\b",
                "", t
            ).strip()
            query = re.sub(r"\s+", " ", query).strip()
            if query:
                asyncio.run(spotify_rechercher(query))
            else:
                asyncio.run(spotify_lecture_pause())
        except Exception as e:
            print(f"[voice] Spotify : {e}")

    def _handle_deezer(self, text: str):
        try:
            from deezer_controller import (deezer_rechercher, deezer_ouvrir,
                                            deezer_lecture_pause, deezer_suivant,
                                            deezer_precedent, deezer_stop)
            t = text.lower()
            if any(w in t for w in ["pause", "stop", "arrête"]):
                asyncio.run(deezer_stop())
                return
            if any(w in t for w in ["suivant", "next"]):
                asyncio.run(deezer_suivant())
                return
            if any(w in t for w in ["précédent", "previous"]):
                asyncio.run(deezer_precedent())
                return
            query = re.sub(
                r"\b(mets|joue|lance|play|écouter?|deezer|musique|chanson|sur deezer)\b",
                "", t
            ).strip()
            query = re.sub(r"\s+", " ", query).strip()
            if query:
                asyncio.run(deezer_rechercher(query))
            else:
                asyncio.run(deezer_ouvrir())
        except Exception as e:
            print(f"[voice] Deezer : {e}")

    def _handle_file(self, text: str):
        try:
            from file_manager import (ouvrir_dossier, trier_par_type,
                                       trier_par_date, arranger_fenetres_dossiers)
            t = text.lower()
            if "trie" in t or "classe" in t:
                _, msg = trier_par_date() if "date" in t else trier_par_type()
                self._tts.speak(msg)
                return
            if any(w in t for w in ["mosaïque", "dispose", "arrange"]):
                self._tts.speak(arranger_fenetres_dossiers())
                return
            for mot in ["bureau", "desktop", "documents", "téléchargements", "downloads",
                        "images", "photos", "musique", "vidéos", "corbeille"]:
                if mot in t:
                    ok, _ = ouvrir_dossier(mot)
                    if ok:
                        self._tts.speak(f"J'ouvre {mot}.")
                    return
        except Exception as e:
            print(f"[voice] FileManager : {e}")

    def _handle_google_docs(self, text: str):
        t = text.lower()
        try:
            from google_services import (creer_google_doc, modifier_google_doc,
                                          ouvrir_google_docs_accueil)
            if any(w in t for w in ["modifie", "ajoute dans", "écris dans", "complète"]):
                # Extraire le contenu à ajouter
                contenu = re.sub(
                    r"\b(modifie|ajoute|écris|dans le document|dans le doc|complète)\b",
                    "", t
                ).strip()
                self._tts.speak(modifier_google_doc(contenu))
                return
            if any(w in t for w in ["crée", "créer", "nouveau"]):
                titre_m = re.search(r'(?:intitulé|nommé|appelé|titre)\s+"?([^"]+)"?', t)
                titre   = titre_m.group(1).strip().title() if titre_m else "Nouveau Document"
                threading.Thread(
                    target=lambda: self._tts.speak(creer_google_doc(titre)),
                    daemon=True,
                ).start()
                return
            # Ouvrir la page d'accueil Google Docs
            self._tts.speak(ouvrir_google_docs_accueil())
        except Exception as e:
            print(f"[voice] Google Docs : {e}")
            self._tts.speak("Google Docs non disponible. Vérifiez credentials.json, Harry.")

    def _handle_google_calendar(self, text: str):
        t = text.lower()
        try:
            from google_services import (lister_evenements_calendar,
                                          ouvrir_google_calendar)
            if any(w in t for w in ["crée", "ajoute", "nouveau rendez-vous", "nouvel événement"]):
                self._calendar_flow.start()
                return
            if any(w in t for w in ["ouvre", "affiche", "montre"]):
                self._tts.speak(ouvrir_google_calendar())
                return
            # Lister les événements
            threading.Thread(
                target=lambda: self._tts.speak(lister_evenements_calendar()),
                daemon=True,
            ).start()
        except Exception as e:
            print(f"[voice] Google Calendar : {e}")
            self._tts.speak("Google Calendar non disponible. Vérifiez credentials.json, Harry.")

    def _handle_google_sheets(self, text: str):
        t = text.lower()
        try:
            from google_services import creer_google_sheet, ouvrir_google_sheets_accueil
            if any(w in t for w in ["crée", "créer", "nouvelle", "nouveau"]):
                titre_m = re.search(r'(?:intitulée?|nommée?|appelée?)\s+"?([^"]+)"?', t)
                titre   = titre_m.group(1).strip().title() if titre_m else "Nouvelle Feuille"
                threading.Thread(
                    target=lambda: self._tts.speak(creer_google_sheet(titre)),
                    daemon=True,
                ).start()
                return
            self._tts.speak(ouvrir_google_sheets_accueil())
        except Exception as e:
            print(f"[voice] Google Sheets : {e}")
            self._tts.speak("Google Sheets non disponible. Vérifiez credentials.json, Harry.")

    def _handle_read_email(self):
        try:
            from google_services import lire_emails
            self._tts.speak(lire_emails())
        except Exception as e:
            print(f"[voice] Lecture emails : {e}")
            self._tts.speak("Impossible de lire vos emails. Vérifiez credentials.json, Harry.")

    def _stop_audio(self):
        """Arrête le TTS en cours (appelé par le frontend via stop_audio)."""
        try:
            self._tts.stop()
        except Exception:
            pass
        _ws.send_state("idle")

    def _toggle_mic(self):
        """Active/désactive le micro depuis le frontend."""
        self._mic_enabled = not self._mic_enabled
        etat = "activé" if self._mic_enabled else "désactivé"
        print(f"[voice] Micro {etat}")
        _ws.send_notification("Microphone", f"Microphone {etat}")

    def _handle_iron_man(self, text: str):
        """Active ou désactive le mode Iron Man depuis une commande vocale."""
        if self._iron_man is None:
            self._tts.speak("Module Iron Man non disponible, Harry.")
            return
        t = text.lower()
        if any(w in t for w in ["active", "démarre", "on", "allume"]):
            self._iron_man.start()
            _ws.send_iron_man("on")
        else:
            self._iron_man.stop()
            _ws.send_iron_man("off")

    def _handle_dictee(self, text: str):
        """Tape le texte demandé à la position actuelle du curseur."""
        try:
            import pyperclip
            import pyautogui
            t = text.lower()
            # Extraire le texte après le déclencheur
            texte_a_taper = text
            for trigger in ["tape ", "dicte ", "dictée ", "Tape ", "Dicte "]:
                idx = text.find(trigger)
                if idx != -1:
                    texte_a_taper = text[idx + len(trigger):].strip()
                    break
            if not texte_a_taper:
                self._tts.speak("Que dois-je taper, Harry ?")
                return
            # Courte pause pour que l'utilisateur repositionne le curseur si besoin
            time.sleep(0.5)
            pyperclip.copy(texte_a_taper)
            pyautogui.hotkey("ctrl", "v")
            short = texte_a_taper[:60] + ("…" if len(texte_a_taper) > 60 else "")
            self._tts.speak(f"J'ai tapé : {short}")
        except ImportError:
            self._tts.speak("pyautogui ou pyperclip manquant pour la dictée.")
        except Exception as e:
            print(f"[voice] Dictée : {e}")
            self._tts.speak("Impossible d'effectuer la dictée.")

    async def _run_mode_boulot(self):
        try:
            from app_launcher import mode_boulot
            self._tts.speak(await mode_boulot(tts_speak=self._tts.speak))
        except Exception as e:
            print(f"[voice] Mode boulot : {e}")

    async def _run_vision(self, text: str):
        try:
            from vision_module import jarvis_vision_cliquer, jarvis_vision_analyser_ecran
            t = text.lower()
            if any(w in t for w in ["clique sur", "appuie sur"]):
                result = await jarvis_vision_cliquer(text)
            else:
                result = await jarvis_vision_analyser_ecran(text)
            self._tts.speak(result)
        except Exception as e:
            print(f"[voice] Vision : {e}")
            self._tts.speak("Vision non disponible.")

    async def _run_camera(self, text: str):
        try:
            from vision_module import jarvis_vision_camera
            self._tts.speak(await jarvis_vision_camera(text))
        except Exception as e:
            print(f"[voice] Camera : {e}")

    # ── Feedback WebView ──────────────────────────────────────────────────────

    def _signal_listening(self):
        win = self._win()
        if not win:
            return
        try:
            win.evaluate_js("window.jarvisListening && window.jarvisListening()")
            win.evaluate_js("window.onWakeWordDetected && window.onWakeWordDetected()")
        except Exception:
            pass

    def _inject_ui(self, text: str):
        win = self._win()
        if not win:
            return
        try:
            win.evaluate_js(
                f"window.handleVoiceInput && window.handleVoiceInput({json.dumps(text)})"
            )
        except Exception:
            pass

    # ── Appel backend SSE ─────────────────────────────────────────────────────

    def _call_backend(self, text: str) -> str:
        _ws.send_state("thinking")
        token = self._get_token()
        if not token:
            return "Je ne suis pas connecté au backend."
        try:
            resp = requests.get(
                f"{BACKEND}/api/v1/chat/stream",
                params={"content": text},
                headers={"Authorization": f"Bearer {token}"},
                stream=True,
                timeout=60,
            )
            if not resp.ok:
                return "Erreur du backend."
            full = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                    if data.get("token"):
                        full += data["token"]
                    if data.get("done") or data.get("error"):
                        break
                except Exception:
                    pass
            return full.strip()
        except Exception as exc:
            print(f"[voice] Backend : {exc}")
            return ""

    def _get_token(self) -> str | None:
        win = self._win()
        if not win:
            return None
        try:
            return win.evaluate_js("localStorage.getItem('jarvis_token')")
        except Exception:
            return None
