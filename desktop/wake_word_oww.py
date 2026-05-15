"""
Wake word OpenWakeWord — alternative gratuite à Porcupine.
Télécharge hey_jarvis au premier lancement ; repli sur "alexa" si indisponible.
Usage : start_wake_word_listener(callback)
"""
import pyaudio
import numpy as np
import threading


def _load_model():
    """
    Essaie de charger hey_jarvis (téléchargement auto si absent),
    puis se rabat sur alexa (fourni par défaut avec openwakeword).
    Retourne (model, model_name).
    """
    from openwakeword.model import Model

    # 1. Tentative avec hey_jarvis (téléchargement automatique)
    try:
        import openwakeword
        openwakeword.utils.download_models(["hey_jarvis"])
        model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        print("[OWW] Modèle actif : hey_jarvis")
        return model, "hey_jarvis"
    except Exception as exc:
        print(f"[OWW] hey_jarvis indisponible ({exc}) — repli sur alexa")

    # 2. Repli sur alexa (inclus par défaut dans openwakeword)
    try:
        model = Model(wakeword_models=["alexa"], inference_framework="onnx")
        print("[OWW] Modèle fallback : alexa  (dites « Alexa » pour activer JARVIS)")
        return model, "alexa"
    except Exception as exc:
        raise RuntimeError(f"Aucun modèle OWW disponible : {exc}")


def start_wake_word_listener(on_detected_callback) -> bool:
    """
    Démarre l'écoute en arrière-plan.
    Retourne True si le listener a démarré, False si OWW n'est pas disponible.
    """
    try:
        model, model_name = _load_model()

        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1280,
        )

        def listen_loop():
            print(f"[OWW] En écoute — modèle : {model_name}")
            state = {"cooldown": False}

            def reset_cooldown():
                state["cooldown"] = False

            while True:
                try:
                    raw         = stream.read(1280, exception_on_overflow=False)
                    audio_array = np.frombuffer(raw, dtype=np.int16)
                    prediction  = model.predict(audio_array)
                    score       = prediction.get(model_name, 0)

                    if score > 0.5 and not state["cooldown"]:
                        print(f"[OWW] Détecté ({model_name}) — score : {score:.2f}")
                        state["cooldown"] = True
                        on_detected_callback()
                        threading.Timer(2.0, reset_cooldown).start()

                except Exception as exc:
                    print(f"[OWW] Erreur audio : {exc}")
                    continue

        threading.Thread(target=listen_loop, daemon=True).start()
        return True

    except Exception as exc:
        print(f"[OWW] Non disponible : {exc}")
        return False
