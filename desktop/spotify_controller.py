"""
Contrôle Spotify — via touches médias globales + win32gui pour le focus.
Fonctionne sans Spotify Web API (pas de token nécessaire).
"""
import os
import re
import subprocess
import time
import asyncio

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


def _focus_spotify() -> bool:
    """Met la fenêtre Spotify au premier plan. Retourne True si trouvé."""
    try:
        import win32gui, win32con
        candidats = []
        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and "Spotify" in win32gui.GetWindowText(hwnd):
                candidats.append(hwnd)
        win32gui.EnumWindows(_cb, None)
        if not candidats:
            return False
        win32gui.ShowWindow(candidats[0], win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(candidats[0])
        time.sleep(0.4)
        return True
    except Exception:
        return False


def spotify_lancer_playlist(playlist_uri: str = "") -> bool:
    """Ouvre Spotify et lance une playlist/piste par son URI ou URL web.
    Convertit automatiquement https://open.spotify.com/... → spotify:type:id."""
    try:
        if playlist_uri.startswith("https://open.spotify.com/"):
            m = re.search(r"/(track|playlist|album|artist)/([A-Za-z0-9]+)", playlist_uri)
            if m:
                playlist_uri = f"spotify:{m.group(1)}:{m.group(2)}"

        deja_ouvert = False
        try:
            deja_ouvert = _focus_spotify()
        except Exception:
            pass

        if playlist_uri:
            subprocess.Popen(["explorer", playlist_uri], shell=False)
            time.sleep(3)
        elif not deja_ouvert:
            chemin = os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")
            if os.path.exists(chemin):
                subprocess.Popen([chemin])
            else:
                subprocess.Popen(["explorer", "spotify:"], shell=False)
            time.sleep(4)

        try:
            _focus_spotify()
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[SPOTIFY] Erreur lancement playlist : {e}")
        return False


async def spotify_ouvrir() -> str:
    if _focus_spotify():
        return "Spotify est déjà ouvert, je l'ai mis au premier plan."
    chemin = os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")
    if os.path.exists(chemin):
        subprocess.Popen([chemin])
    else:
        subprocess.Popen(["explorer", "spotify:"], shell=False)
    time.sleep(4)
    _focus_spotify()
    return "Spotify lancé."


async def spotify_lecture_pause() -> str:
    if pyautogui:
        pyautogui.press("playpause")
    return "Lecture/Pause."


async def spotify_suivant() -> str:
    if pyautogui:
        pyautogui.press("nexttrack")
    return "Piste suivante."


async def spotify_precedent() -> str:
    if pyautogui:
        pyautogui.press("prevtrack")
    return "Piste précédente."


async def spotify_stop() -> str:
    _focus_spotify()
    time.sleep(0.2)
    if pyautogui:
        pyautogui.press("playpause")
    return "Musique mise en pause."


async def spotify_volume(direction: str, paliers: int = 4) -> str:
    if not _focus_spotify():
        return "Spotify ne semble pas ouvert."
    time.sleep(0.2)
    if pyautogui:
        for _ in range(paliers):
            if direction in ("monter", "up", "augmenter", "plus"):
                pyautogui.hotkey("ctrl", "up")
            else:
                pyautogui.hotkey("ctrl", "down")
            time.sleep(0.05)
    msg = "Volume monté" if direction in ("monter", "up", "augmenter", "plus") else "Volume baissé"
    return f"{msg} sur Spotify."


async def spotify_rechercher(recherche: str) -> str:
    """Ouvre la barre de recherche Spotify, tape la requête et lance la lecture."""
    if not pyautogui or not pyperclip:
        return "pyautogui ou pyperclip manquant."

    if not _focus_spotify():
        await spotify_ouvrir()
        time.sleep(3)
        _focus_spotify()
    time.sleep(0.5)

    # Ctrl+L puis Ctrl+K (compatibilité ancienne/nouvelle interface)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "k")
    time.sleep(0.4)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyperclip.copy(recherche)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(2.0)
    pyautogui.press("enter")
    time.sleep(1.0)
    pyautogui.press("enter")

    return f"Je lance '{recherche}' sur Spotify."
