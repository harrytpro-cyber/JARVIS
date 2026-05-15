"""
Vision IA — Gemini Vision via REST pour analyser / cliquer sur l'écran.
Nécessite : GEMINI_API_KEY dans .env, pyautogui, Pillow.
Optionnel  : opencv-python pour la caméra.
"""
import asyncio
import base64
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import cv2
except ImportError:
    cv2 = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
_GEMINI_URL    = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


# ── Appel Gemini Vision ────────────────────────────────────────────────

def _gemini_vision(prompt: str, image_b64: str, mime: str = "image/png") -> str:
    """Appelle l'API Gemini Vision et retourne le texte généré."""
    if not GEMINI_API_KEY:
        return "GEMINI_API_KEY non configurée dans .env"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": image_b64}},
            ]
        }]
    }
    r    = requests.post(_GEMINI_URL, params={"key": GEMINI_API_KEY}, json=payload, timeout=30)
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        print(f"[VISION] Réponse inattendue : {data}")
        return "Je n'ai pas pu analyser l'image."


def _screenshot_b64() -> tuple[str, int, int]:
    """Capture l'écran et retourne (base64_png, largeur, hauteur)."""
    if not pyautogui or not Image:
        return "", 0, 0
    screenshot = pyautogui.screenshot()
    img_w, img_h = screenshot.size
    tmp_path = os.path.join(os.environ.get("TEMP", "."), "jarvis_vision_temp.png")
    screenshot.save(tmp_path)
    with open(tmp_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    try:
        os.remove(tmp_path)
    except Exception:
        pass
    return b64, img_w, img_h


def _coords_depuis_box(box: list, img_w: int, img_h: int) -> tuple[int, int]:
    """Convertit [ymin, xmin, ymax, xmax] (0-1000) en pixels réels."""
    ymin, xmin, ymax, xmax = box
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    return int(cx / 1000 * img_w), int(cy / 1000 * img_h)


# ── Fonctions publiques ────────────────────────────────────────────────

async def jarvis_vision_cliquer(instruction: str) -> str:
    """Analyse l'écran et clique sur l'élément décrit par l'instruction."""
    if not pyautogui or not Image:
        return "pyautogui ou Pillow manquant."

    await asyncio.sleep(0.5)
    b64, img_w, img_h = _screenshot_b64()
    if not b64:
        return "Impossible de capturer l'écran."

    prompt = (
        f"Tu es l'œil de JARVIS. Voici une capture d'écran ({img_w}x{img_h} pixels).\n"
        f"Instruction : {instruction}\n"
        "Trouve l'élément demandé (bouton, texte, icône, item de liste).\n"
        "Réponds UNIQUEMENT en JSON :\n"
        "{\"box\": [ymin, xmin, ymax, xmax], \"description\": \"description courte\"}\n"
        "Coordonnées normalisées de 0 à 1000 (0=haut-gauche, 1000=bas-droite)."
    )

    rep = _gemini_vision(prompt, b64)
    print(f"[VISION] Gemini : {rep}")

    try:
        start = rep.find("{")
        end   = rep.rfind("}") + 1
        data  = json.loads(rep[start:end])
        box   = data.get("box", [500, 500, 500, 500])
        tx, ty = _coords_depuis_box(box, img_w, img_h)
        desc  = data.get("description", instruction)

        print(f"[VISION] Cible : {desc} à ({tx}, {ty})")
        pyautogui.moveTo(tx, ty, duration=0.5)
        time.sleep(0.2)

        # Double-clic pour les éléments de liste (musique, fichier, etc.)
        t = instruction.lower()
        if any(k in t for k in ["musique", "chanson", "piste", "numéro", "numero", "titre", "fichier"]):
            pyautogui.doubleClick()
        else:
            pyautogui.click()

        return f"J'ai cliqué sur : {desc}."
    except Exception as e:
        print(f"[VISION] Erreur parsing : {e}")
        return "Je vois l'interface, mais je n'ai pas réussi à identifier l'élément précis."


async def jarvis_vision_ecrire(instruction: str, texte_a_taper: str) -> str:
    """Localise un champ de texte et y tape le contenu."""
    if not pyautogui or not Image:
        return "pyautogui ou Pillow manquant."

    try:
        import pyperclip
    except ImportError:
        return "pyperclip manquant."

    b64, img_w, img_h = _screenshot_b64()
    if not b64:
        return "Impossible de capturer l'écran."

    prompt = (
        f"Tu es la vision de JARVIS. Je veux écrire dans le champ : {instruction}.\n"
        f"Résolution : {img_w}x{img_h} pixels.\n"
        "Trouve EXACTEMENT la position de ce champ de saisie.\n"
        "Coordonnées normalisées de 0 à 1000.\n"
        "Réponds UNIQUEMENT en JSON :\n"
        "{\"box\": [ymin, xmin, ymax, xmax], \"description\": \"description du champ\"}"
    )

    rep = _gemini_vision(prompt, b64)
    try:
        start = rep.find("{")
        end   = rep.rfind("}") + 1
        data  = json.loads(rep[start:end])
        box   = data.get("box", [500, 500, 500, 500])
        tx, ty = _coords_depuis_box(box, img_w, img_h)

        pyautogui.moveTo(tx, ty, duration=0.5)
        time.sleep(0.15)
        pyautogui.click()
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyperclip.copy(texte_a_taper)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        pyautogui.press("enter")

        return f"J'ai saisi '{texte_a_taper}' dans {instruction}."
    except Exception as e:
        print(f"[VISION] Erreur écriture : {e}")
        return "J'ai eu un problème technique pour taper le texte."


async def jarvis_vision_rechercher_sur_site(texte: str) -> str:
    """Trouve la barre de recherche sur la page visible et tape la requête."""
    if not pyautogui or not Image:
        return "pyautogui ou Pillow manquant."

    try:
        import pyperclip
    except ImportError:
        return "pyperclip manquant."

    b64, img_w, img_h = _screenshot_b64()
    if not b64:
        return "Impossible de capturer l'écran."

    prompt = (
        f"Tu es la vision de JARVIS. Je veux rechercher : {texte}\n"
        f"Résolution : {img_w}x{img_h} pixels.\n"
        "Localise la BARRE DE RECHERCHE principale du site affiché "
        "(champ avec icône loupe, placeholder 'Search', 'Rechercher'…).\n"
        "Si tu vois une barre d'adresse navigateur ET une barre du site, préfère celle du site.\n"
        "Coordonnées normalisées de 0 à 1000.\n"
        "Réponds UNIQUEMENT en JSON :\n"
        "{\"box\": [ymin, xmin, ymax, xmax], \"description\": \"description\"}"
    )

    rep = _gemini_vision(prompt, b64)
    try:
        start = rep.find("{")
        end   = rep.rfind("}") + 1
        data  = json.loads(rep[start:end])
        box   = data.get("box", [500, 500, 500, 500])
        tx, ty = _coords_depuis_box(box, img_w, img_h)
        desc  = data.get("description", "barre de recherche")

        pyautogui.moveTo(tx, ty, duration=0.5)
        time.sleep(0.15)
        pyautogui.click()
        time.sleep(0.35)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyperclip.copy(texte)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.15)
        pyautogui.press("enter")

        return f"J'ai tapé '{texte}' dans la {desc}."
    except Exception as e:
        print(f"[VISION] Erreur recherche site : {e}")
        return "Je n'ai pas réussi à trouver la barre de recherche."


async def jarvis_vision_camera(question: str = None) -> str:
    """Capture la webcam et analyse l'image avec Gemini Vision."""
    if cv2 is None:
        return "OpenCV (opencv-python) n'est pas installé."

    cap = None
    try:
        for idx in [0, 1]:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                break
            cap.release()

        if not cap or not cap.isOpened():
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "Je n'arrive pas à accéder à votre caméra."

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Laisser la caméra s'ajuster
        start = time.time()
        while time.time() - start < 2.0:
            cap.read()
            await asyncio.sleep(0.1)

        ret, frame = cap.read()
        if not ret or frame is None:
            return "La capture webcam a échoué."

        tmp = os.path.join(os.environ.get("TEMP", "."), "jarvis_camera_temp.jpg")
        cv2.imwrite(tmp, frame)
        with open(tmp, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        try:
            os.remove(tmp)
        except Exception:
            pass

        prompt = (
            f"Analyse cette image capturée par la caméra de l'utilisateur. "
            f"Sa demande : '{question or 'Décris ce que tu vois'}'. "
            "Réponds en français de façon concise."
        )
        return _gemini_vision(prompt, b64, mime="image/jpeg")

    except Exception as e:
        print(f"[CAMERA] Erreur : {e}")
        return f"Erreur caméra : {e}"
    finally:
        if cap:
            cap.release()


async def jarvis_vision_analyser_ecran(question: str = None) -> str:
    """Capture et décrit l'écran sans cliquer — pour répondre à 'qu'est-ce qui est affiché ?'"""
    b64, img_w, img_h = _screenshot_b64()
    if not b64:
        return "Impossible de capturer l'écran."

    prompt = (
        f"Analyse cette capture d'écran ({img_w}x{img_h} pixels).\n"
        f"Demande : '{question or 'Décris ce qui est affiché'}'\n"
        "Réponds en français de façon concise et utile."
    )
    return _gemini_vision(prompt, b64)
