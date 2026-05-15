"""
Lanceur d'applications Windows — détection universelle.
Ordre : registre Windows → PATH système → chemins hints → jarvis_config.json (custom).
"""
import os
import subprocess
import shutil
import time
import asyncio

try:
    import psutil
except ImportError:
    psutil = None


# ── Détection universelle ──────────────────────────────────────────────

def _trouver_exe(noms_exe: list, chemins_hints: list = None) -> str:
    """Registre → PATH → hints. Retourne le chemin ou chaîne vide."""
    try:
        import winreg
        for exe in noms_exe:
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    key = winreg.OpenKey(
                        hive,
                        f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exe}"
                    )
                    path, _ = winreg.QueryValueEx(key, "")
                    winreg.CloseKey(key)
                    p = os.path.expandvars(path.strip('"'))
                    if os.path.exists(p):
                        return p
                except Exception:
                    pass
    except ImportError:
        pass

    for exe in noms_exe:
        found = shutil.which(exe)
        if found:
            return found

    if chemins_hints:
        for hint in chemins_hints:
            p = os.path.expandvars(hint)
            if os.path.exists(p):
                return p
    return ""


def _lancer(label: str, noms_exe: list, chemins_hints: list = None, env_key: str = None) -> bool:
    """Lance une application sans popup d'erreur Windows."""
    if env_key:
        env_val = os.path.expandvars(os.getenv(env_key, ""))
        if env_val and os.path.exists(env_val):
            try:
                subprocess.Popen([env_val])
                return True
            except Exception:
                pass

    exe_path = _trouver_exe(noms_exe, chemins_hints)
    if exe_path:
        try:
            subprocess.Popen([exe_path])
            return True
        except Exception:
            pass

    print(f"[APP] {label} introuvable (registre, PATH et hints épuisés)")
    return False


def _fermer(noms_process: list) -> bool:
    """Termine tous les processus correspondant aux noms donnés."""
    if psutil is None:
        return False
    tues = 0
    noms_lower = [n.lower() for n in noms_process]
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() in noms_lower:
                proc.terminate()
                tues += 1
        except Exception:
            pass
    return tues > 0


# ── Catalogue d'applications ───────────────────────────────────────────

_APPS_CATALOGUE: dict = {
    # ── Navigateurs ──────────────────────────────────────────
    "chrome": {
        "label": "Google Chrome", "noms": ["chrome.exe"],
        "hints": [
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
        ],
    },
    "firefox": {
        "label": "Firefox", "noms": ["firefox.exe"],
        "hints": [
            r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe",
            r"%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe",
        ],
    },
    "edge": {
        "label": "Microsoft Edge", "noms": ["msedge.exe"],
        "hints": [
            r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
            r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        ],
    },
    "opera": {
        "label": "Opera", "noms": ["opera.exe"],
        "hints": [
            r"%LOCALAPPDATA%\Programs\Opera\opera.exe",
            r"%LOCALAPPDATA%\Programs\Opera GX\opera.exe",
            r"%APPDATA%\Opera Software\Opera Stable\opera.exe",
            r"%APPDATA%\Opera Software\Opera GX Stable\opera.exe",
        ],
    },
    "brave": {
        "label": "Brave", "noms": ["brave.exe"],
        "hints": [
            r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe",
        ],
    },
    # ── Jeux / Launchers ─────────────────────────────────────
    "steam": {
        "label": "Steam", "noms": ["steam.exe"],
        "hints": [r"%PROGRAMFILES(X86)%\Steam\steam.exe", r"%PROGRAMFILES%\Steam\steam.exe"],
    },
    "epic": {
        "label": "Epic Games", "noms": ["EpicGamesLauncher.exe"],
        "hints": [
            r"%PROGRAMFILES(X86)%\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
            r"%PROGRAMFILES%\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        ],
    },
    "ea": {
        "label": "EA App", "noms": ["EADesktop.exe", "EA.exe"],
        "hints": [
            r"%PROGRAMFILES%\Electronic Arts\EA Desktop\EA Desktop.exe",
            r"%PROGRAMFILES(X86)%\Electronic Arts\EA Desktop\EA Desktop.exe",
        ],
    },
    "ubisoft": {
        "label": "Ubisoft Connect", "noms": ["UbisoftConnect.exe", "upc.exe"],
        "hints": [
            r"%PROGRAMFILES(X86)%\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
            r"%PROGRAMFILES%\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
        ],
    },
    "gog": {
        "label": "GOG Galaxy", "noms": ["GalaxyClient.exe"],
        "hints": [
            r"%PROGRAMFILES(X86)%\GOG Galaxy\GalaxyClient.exe",
            r"%PROGRAMFILES%\GOG Galaxy\GalaxyClient.exe",
        ],
    },
    "minecraft": {
        "label": "Minecraft", "noms": ["Minecraft.exe", "MinecraftLauncher.exe"],
        "hints": [r"%PROGRAMFILES(X86)%\Minecraft Launcher\MinecraftLauncher.exe"],
    },
    # ── Communication ────────────────────────────────────────
    "discord": {
        "label": "Discord", "noms": ["Discord.exe"],
        "hints": [
            r"%LOCALAPPDATA%\Discord\Update.exe",
            r"%APPDATA%\Discord\Update.exe",
        ],
    },
    "teams": {
        "label": "Microsoft Teams", "noms": ["ms-teams.exe", "Teams.exe"],
        "hints": [
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\ms-teams.exe",
            r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",
        ],
    },
    "whatsapp": {
        "label": "WhatsApp", "noms": ["WhatsApp.exe"],
        "hints": [
            r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
            r"%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe",
        ],
    },
    "telegram": {
        "label": "Telegram", "noms": ["Telegram.exe"],
        "hints": [
            r"%APPDATA%\Telegram Desktop\Telegram.exe",
            r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe",
        ],
    },
    "zoom": {
        "label": "Zoom", "noms": ["Zoom.exe"],
        "hints": [
            r"%APPDATA%\Zoom\bin\Zoom.exe",
            r"%PROGRAMFILES%\Zoom\bin\Zoom.exe",
        ],
    },
    "skype": {
        "label": "Skype", "noms": ["Skype.exe"],
        "hints": [r"%LOCALAPPDATA%\Microsoft\WindowsApps\Skype.exe"],
    },
    # ── Bureautique / Office ─────────────────────────────────
    "word": {
        "label": "Microsoft Word", "noms": ["WINWORD.EXE", "winword.exe"],
        "hints": [
            r"%PROGRAMFILES%\Microsoft Office\root\Office16\WINWORD.EXE",
            r"%PROGRAMFILES(X86)%\Microsoft Office\root\Office16\WINWORD.EXE",
        ],
    },
    "excel": {
        "label": "Microsoft Excel", "noms": ["EXCEL.EXE", "excel.exe"],
        "hints": [
            r"%PROGRAMFILES%\Microsoft Office\root\Office16\EXCEL.EXE",
            r"%PROGRAMFILES(X86)%\Microsoft Office\root\Office16\EXCEL.EXE",
        ],
    },
    "powerpoint": {
        "label": "Microsoft PowerPoint", "noms": ["POWERPNT.EXE", "powerpnt.exe"],
        "hints": [
            r"%PROGRAMFILES%\Microsoft Office\root\Office16\POWERPNT.EXE",
            r"%PROGRAMFILES(X86)%\Microsoft Office\root\Office16\POWERPNT.EXE",
        ],
    },
    "outlook": {
        "label": "Outlook", "noms": ["OUTLOOK.EXE", "outlook.exe", "olk.exe"],
        "hints": [
            r"%PROGRAMFILES%\Microsoft Office\root\Office16\OUTLOOK.EXE",
            r"%PROGRAMFILES(X86)%\Microsoft Office\root\Office16\OUTLOOK.EXE",
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\olk.exe",
        ],
    },
    "onenote": {
        "label": "OneNote", "noms": ["ONENOTE.EXE", "onenote.exe"],
        "hints": [
            r"%PROGRAMFILES%\Microsoft Office\root\Office16\ONENOTE.EXE",
            r"%PROGRAMFILES(X86)%\Microsoft Office\root\Office16\ONENOTE.EXE",
        ],
    },
    # ── Créatif / Design ─────────────────────────────────────
    "photoshop": {
        "label": "Photoshop", "noms": ["Photoshop.exe"],
        "hints": [
            r"%PROGRAMFILES%\Adobe\Adobe Photoshop 2025\Photoshop.exe",
            r"%PROGRAMFILES%\Adobe\Adobe Photoshop 2024\Photoshop.exe",
            r"%PROGRAMFILES%\Adobe\Adobe Photoshop 2023\Photoshop.exe",
        ],
    },
    "premiere": {
        "label": "Premiere Pro", "noms": ["Adobe Premiere Pro.exe"],
        "hints": [
            r"%PROGRAMFILES%\Adobe\Adobe Premiere Pro 2025\Adobe Premiere Pro.exe",
            r"%PROGRAMFILES%\Adobe\Adobe Premiere Pro 2024\Adobe Premiere Pro.exe",
        ],
    },
    "after effects": {
        "label": "After Effects", "noms": ["AfterFX.exe"],
        "hints": [
            r"%PROGRAMFILES%\Adobe\Adobe After Effects 2025\Support Files\AfterFX.exe",
            r"%PROGRAMFILES%\Adobe\Adobe After Effects 2024\Support Files\AfterFX.exe",
        ],
    },
    "illustrator": {
        "label": "Illustrator", "noms": ["Illustrator.exe"],
        "hints": [
            r"%PROGRAMFILES%\Adobe\Adobe Illustrator 2025\Support Files\Contents\Windows\Illustrator.exe",
            r"%PROGRAMFILES%\Adobe\Adobe Illustrator 2024\Support Files\Contents\Windows\Illustrator.exe",
        ],
    },
    "capcut": {
        "label": "CapCut", "noms": ["CapCut.exe"],
        "hints": [
            r"%LOCALAPPDATA%\CapCut\Apps\CapCut.exe",
            r"%PROGRAMFILES%\CapCut\CapCut.exe",
        ],
    },
    "obs": {
        "label": "OBS Studio", "noms": ["obs64.exe", "obs32.exe"],
        "hints": [
            r"%PROGRAMFILES%\obs-studio\bin\64bit\obs64.exe",
            r"%PROGRAMFILES(X86)%\obs-studio\bin\64bit\obs64.exe",
        ],
    },
    "blender": {
        "label": "Blender", "noms": ["blender.exe"],
        "hints": [
            r"%PROGRAMFILES%\Blender Foundation\Blender 4.0\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender 3.6\blender.exe",
            r"%PROGRAMFILES%\Blender Foundation\Blender\blender.exe",
        ],
    },
    "gimp": {
        "label": "GIMP", "noms": ["gimp-2.10.exe", "gimp.exe"],
        "hints": [
            r"%PROGRAMFILES%\GIMP 2\bin\gimp-2.10.exe",
            r"%PROGRAMFILES(X86)%\GIMP 2\bin\gimp-2.10.exe",
        ],
    },
    # ── Développement ────────────────────────────────────────
    "vscode": {
        "label": "Visual Studio Code", "noms": ["Code.exe"],
        "hints": [
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
        ],
    },
    "claude": {
        "label": "Claude", "noms": ["claude.exe", "Claude.exe"],
        "hints": [
            r"%LOCALAPPDATA%\AnthropicClaude\claude.exe",
            r"%PROGRAMFILES%\AnthropicClaude\claude.exe",
        ],
    },
    "terminal": {
        "label": "Terminal Windows", "noms": ["wt.exe", "WindowsTerminal.exe"],
        "hints": [r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"],
    },
    # ── Multimédia ───────────────────────────────────────────
    "vlc": {
        "label": "VLC", "noms": ["vlc.exe"],
        "hints": [
            r"%PROGRAMFILES%\VideoLAN\VLC\vlc.exe",
            r"%PROGRAMFILES(X86)%\VideoLAN\VLC\vlc.exe",
        ],
    },
    "spotify": {
        "label": "Spotify", "noms": ["Spotify.exe"],
        "hints": [
            r"%APPDATA%\Spotify\Spotify.exe",
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe",
        ],
    },
    "deezer": {
        "label": "Deezer", "noms": ["deezer.exe"],
        "hints": [
            r"%LOCALAPPDATA%\Programs\Deezer\Deezer.exe",
            r"%APPDATA%\Deezer\Deezer.exe",
        ],
    },
    # ── Système / Utilitaires ────────────────────────────────
    "explorateur": {
        "label": "Explorateur de fichiers", "noms": ["explorer.exe"], "hints": [],
    },
    "notepad": {
        "label": "Bloc-notes", "noms": ["notepad.exe"], "hints": [],
    },
    "calculatrice": {
        "label": "Calculatrice", "noms": ["CalculatorApp.exe", "calc.exe"], "hints": [],
    },
    "gestionnaire": {
        "label": "Gestionnaire des tâches", "noms": ["Taskmgr.exe"], "hints": [],
    },
    "filezilla": {
        "label": "FileZilla", "noms": ["filezilla.exe"],
        "hints": [
            r"%PROGRAMFILES%\FileZilla FTP Client\filezilla.exe",
            r"%PROGRAMFILES(X86)%\FileZilla FTP Client\filezilla.exe",
        ],
    },
    "winrar": {
        "label": "WinRAR", "noms": ["WinRAR.exe"],
        "hints": [r"%PROGRAMFILES%\WinRAR\WinRAR.exe", r"%PROGRAMFILES(X86)%\WinRAR\WinRAR.exe"],
    },
    "7zip": {
        "label": "7-Zip", "noms": ["7zFM.exe"],
        "hints": [r"%PROGRAMFILES%\7-Zip\7zFM.exe", r"%PROGRAMFILES(X86)%\7-Zip\7zFM.exe"],
    },
}

# ── Aliases ────────────────────────────────────────────────────────────
_APPS_CATALOGUE.update({
    "google chrome":              _APPS_CATALOGUE["chrome"],
    "microsoft edge":             _APPS_CATALOGUE["edge"],
    "opera gx":                   _APPS_CATALOGUE["opera"],
    "epic games":                 _APPS_CATALOGUE["epic"],
    "epic game":                  _APPS_CATALOGUE["epic"],
    "ea app":                     _APPS_CATALOGUE["ea"],
    "ubisoft connect":            _APPS_CATALOGUE["ubisoft"],
    "uplay":                      _APPS_CATALOGUE["ubisoft"],
    "gog galaxy":                 _APPS_CATALOGUE["gog"],
    "visual studio code":         _APPS_CATALOGUE["vscode"],
    "vs code":                    _APPS_CATALOGUE["vscode"],
    "code":                       _APPS_CATALOGUE["vscode"],
    "microsoft word":             _APPS_CATALOGUE["word"],
    "microsoft excel":            _APPS_CATALOGUE["excel"],
    "microsoft powerpoint":       _APPS_CATALOGUE["powerpoint"],
    "ppt":                        _APPS_CATALOGUE["powerpoint"],
    "microsoft outlook":          _APPS_CATALOGUE["outlook"],
    "microsoft teams":            _APPS_CATALOGUE["teams"],
    "obs studio":                 _APPS_CATALOGUE["obs"],
    "adobe photoshop":            _APPS_CATALOGUE["photoshop"],
    "adobe premiere":             _APPS_CATALOGUE["premiere"],
    "premiere pro":               _APPS_CATALOGUE["premiere"],
    "adobe after effects":        _APPS_CATALOGUE["after effects"],
    "adobe illustrator":          _APPS_CATALOGUE["illustrator"],
    "7 zip":                      _APPS_CATALOGUE["7zip"],
    "sept zip":                   _APPS_CATALOGUE["7zip"],
    "bloc-notes":                 _APPS_CATALOGUE["notepad"],
    "bloc notes":                 _APPS_CATALOGUE["notepad"],
    "task manager":               _APPS_CATALOGUE["gestionnaire"],
    "terminal windows":           _APPS_CATALOGUE["terminal"],
})


def _charger_custom_apps():
    """Charge les apps dynamiques depuis jarvis_config.json."""
    import json
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
        if not os.path.exists(config_path):
            return
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Supprimer les anciens customs
        to_remove = [k for k, v in _APPS_CATALOGUE.items() if isinstance(v, dict) and v.get("is_custom")]
        for k in to_remove:
            del _APPS_CATALOGUE[k]
        # Ajouter les nouveaux
        for app in config.get("custom_apps", []):
            app_id    = app.get("id")
            app_path  = app.get("exe_path")
            app_label = app.get("label", app_id)
            if app_id and app_path:
                exe_name = os.path.basename(app_path.replace("\\", "/"))
                entry = {
                    "label"    : app_label,
                    "noms"     : [exe_name],
                    "hints"    : [app_path],
                    "is_custom": True,
                }
                _APPS_CATALOGUE[app_id] = entry
                if app_label:
                    _APPS_CATALOGUE[app_label.lower()] = entry
    except Exception as e:
        print(f"[APP] Erreur chargement custom apps : {e}")


_charger_custom_apps()


# ── Interface publique ─────────────────────────────────────────────────

class AppLauncher:
    """Lanceur d'applications pour le pipeline vocal JARVIS."""

    def launch(self, text: str) -> str | None:
        """Tente de lancer une app mentionnée dans le texte. Retourne None si rien trouvé."""
        t = text.lower()
        # Tri par longueur de clé décroissante → les alias longs ont priorité
        for key in sorted(_APPS_CATALOGUE.keys(), key=len, reverse=True):
            if key in t:
                info = _APPS_CATALOGUE[key]
                ok   = _lancer(info["label"], info["noms"], info.get("hints"), info.get("env_key"))
                return f"Je lance {info['label']}." if ok else f"Je n'ai pas trouvé {info['label']} sur ce PC."
        return None

    def close(self, text: str) -> str | None:
        """Tente de fermer une app mentionnée dans le texte."""
        t = text.lower()
        for key in sorted(_APPS_CATALOGUE.keys(), key=len, reverse=True):
            if key in t:
                info = _APPS_CATALOGUE[key]
                ok   = _fermer(info["noms"])
                return f"{info['label']} {'fermé.' if ok else 'non trouvé dans les processus.'}"
        return None


async def mode_boulot(tts_speak=None) -> str:
    """Lance Spotify + Documents + Téléchargements + Chrome et dispose en 4 quadrants."""
    try:
        import win32gui, win32con, win32api
    except ImportError:
        return "pywin32 manquant — installez-le pour la disposition des fenêtres."

    if tts_speak:
        tts_speak("Bien, je prépare votre espace de travail.")
    await asyncio.sleep(0.2)

    # 1. Spotify
    _lancer("Spotify", ["Spotify.exe"], [r"%APPDATA%\Spotify\Spotify.exe"])
    time.sleep(0.5)

    # 2. Dossiers Documents + Téléchargements
    from file_manager import resoudre_chemin
    subprocess.Popen(["explorer", resoudre_chemin("documents")])
    time.sleep(0.3)
    subprocess.Popen(["explorer", resoudre_chemin("téléchargements")])
    time.sleep(0.3)

    # 3. Chrome
    _lancer(
        "Chrome", ["chrome.exe"],
        chemins_hints=[
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
        ],
        env_key="CHROME_PATH",
    )
    time.sleep(0.3)

    if tts_speak:
        tts_speak("Applications lancées, j'arrange votre espace dans quelques secondes.")
    await asyncio.sleep(7)

    # 4. Disposition en quadrants
    screen_w = win32api.GetSystemMetrics(0)
    screen_h = win32api.GetSystemMetrics(1)
    work_h   = screen_h - 48
    hw, hh   = screen_w // 2, work_h // 2

    disposition = [
        {"titres": ["Documents"],                         "pos": (0,  0,  hw, hh)},
        {"titres": ["Téléchargements", "Downloads"],      "pos": (hw, 0,  hw, hh)},
        {"titres": ["Chrome", "Google Chrome"],           "pos": (0,  hh, hw, hh)},
        {"titres": ["Spotify"],                           "pos": (hw, hh, hw, hh)},
    ]

    def _find_hwnd(titres):
        found = [None]
        def cb(hwnd, _):
            if found[0]:
                return
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if any(mot.lower() in t.lower() for mot in titres):
                    found[0] = hwnd
        win32gui.EnumWindows(cb, None)
        return found[0]

    ok = 0
    for item in disposition:
        hwnd = _find_hwnd(item["titres"])
        if hwnd:
            x, y, w, h = item["pos"]
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_SHOWWINDOW)
            time.sleep(0.2)
            ok += 1

    return f"Espace de travail prêt — {ok}/4 fenêtres positionnées."
