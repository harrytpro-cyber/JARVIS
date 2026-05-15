"""
Service TTS — edge-tts (voix neurale Microsoft, qualité native) + pygame pour la lecture.
Voix configurée via TTS_VOICE dans le .env (défaut : fr-FR-HenriNeural).
"""
import asyncio
import os
import tempfile
import threading

import pygame
import edge_tts

# System prompt injecté dans les appels backend depuis le pipeline vocal
VOICE_SYSTEM_PROMPT = """Tu es JARVIS, assistant IA personnel.
Tu réponds TOUJOURS en français, peu importe la langue de la question.
Tes réponses vocales sont courtes — maximum 2 phrases — car elles sont lues à voix haute.
Tu es efficace, légèrement sarcastique, et direct."""


class TTSService:
    def __init__(self):
        self.voice       = os.getenv("TTS_VOICE", "fr-FR-HenriNeural")
        self.is_speaking = False
        self._lock       = threading.Lock()
        pygame.mixer.init()
        print(f"[TTS] Voix active : {self.voice}")

    def speak(self, text: str):
        """Lance la synthèse dans un thread daemon — non bloquant."""
        if not text or not text.strip():
            return
        def _run():
            self.is_speaking = True
            try:
                asyncio.run(self._speak_async(text.strip()))
            except Exception as exc:
                print(f"[TTS] Erreur : {exc}")
            finally:
                self.is_speaking = False
        threading.Thread(target=_run, daemon=True).start()

    async def _speak_async(self, text: str):
        with self._lock:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(tmp_path)
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.05)
                pygame.mixer.music.unload()
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def stop(self):
        """Arrête la lecture en cours."""
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.is_speaking = False
