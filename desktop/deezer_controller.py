"""
Contrôle Deezer — via touches médias globales + win32gui pour le focus.
"""
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


def _focus_deezer() -> bool:
    """Met la fenêtre Deezer au premier plan. Retourne True si trouvé."""
    try:
        import win32gui, win32con
        candidats = []
        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and "Deezer" in win32gui.GetWindowText(hwnd):
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


async def deezer_ouvrir() -> str:
    if _focus_deezer():
        return "Deezer est déjà ouvert, je l'ai mis au premier plan."
    subprocess.Popen(["explorer", "deezer:"], shell=False)
    time.sleep(4)
    _focus_deezer()
    return "Deezer lancé."


async def deezer_lecture_pause() -> str:
    if pyautogui:
        pyautogui.press("playpause")
    return "Lecture/Pause."


async def deezer_suivant() -> str:
    if pyautogui:
        pyautogui.press("nexttrack")
    return "Piste suivante sur Deezer."


async def deezer_precedent() -> str:
    if pyautogui:
        pyautogui.press("prevtrack")
    return "Piste précédente sur Deezer."


async def deezer_stop() -> str:
    _focus_deezer()
    time.sleep(0.2)
    if pyautogui:
        pyautogui.press("playpause")
    return "Musique mise en pause sur Deezer."


async def deezer_volume(direction: str, paliers: int = 4) -> str:
    time.sleep(0.2)
    if pyautogui:
        for _ in range(paliers):
            if direction in ("monter", "up", "augmenter", "plus"):
                pyautogui.press("volumeup")
            else:
                pyautogui.press("volumedown")
            time.sleep(0.05)
    msg = "Volume monté" if direction in ("monter", "up", "augmenter", "plus") else "Volume baissé"
    return f"{msg}."


async def deezer_rechercher(recherche: str) -> str:
    """Focus Deezer, recherche la requête et tente de lancer la lecture."""
    if not pyautogui or not pyperclip:
        return "pyautogui ou pyperclip manquant."

    if not _focus_deezer():
        await deezer_ouvrir()
        time.sleep(3)
        _focus_deezer()
    time.sleep(0.5)

    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyperclip.copy(recherche)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(2.0)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.press("enter")

    return f"Je cherche '{recherche}' sur Deezer."
