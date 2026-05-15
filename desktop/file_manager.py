"""
Gestionnaire de fichiers Windows — commandes vocales.
Ouvrir, lister, trier (par type / par date), renommer, déplacer, chercher.
"""
import os
import shutil
import subprocess
import ctypes
import time
from datetime import datetime
from pathlib import Path

try:
    import pyautogui
except ImportError:
    pyautogui = None

user32 = ctypes.windll.user32

# ── État courant ───────────────────────────────────────────────────────
dossier_courant: str = ""

# ── Catégories de fichiers ─────────────────────────────────────────────
EXTENSIONS: dict[str, set[str]] = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
                    ".ico", ".tiff", ".tif", ".raw", ".heic", ".avif"},
    "Vidéos":      {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
                    ".m4v", ".mpg", ".mpeg", ".3gp", ".ts"},
    "Musique":     {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
                    ".opus", ".aiff"},
    "Documents":   {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                    ".odt", ".ods", ".odp", ".txt", ".rtf", ".csv", ".md"},
    "Code":        {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
                    ".yaml", ".yml", ".sh", ".bat", ".ps1", ".c", ".cpp",
                    ".java", ".cs", ".php", ".rb", ".go", ".rs", ".swift"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"},
    "Exécutables": {".exe", ".msi", ".apk", ".dmg", ".deb"},
}


# ── Résolution de chemins ──────────────────────────────────────────────

def resoudre_chemin(chemin: str) -> str:
    """Convertit un alias vocal ('bureau', 'documents'…) en chemin absolu."""
    if not chemin:
        return ""
    chemin = chemin.strip().strip('"').strip("'")
    raccourcis = {
        "bureau":           os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        "desktop":          os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        "document":         os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
        "documents":        os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
        "téléchargement":   os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "téléchargements":  os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "telechargement":   os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "telechargements":  os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "downloads":        os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "image":            os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
        "images":           os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
        "photo":            os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
        "photos":           os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
        "vidéo":            os.path.join(os.environ.get("USERPROFILE", ""), "Videos"),
        "vidéos":           os.path.join(os.environ.get("USERPROFILE", ""), "Videos"),
        "video":            os.path.join(os.environ.get("USERPROFILE", ""), "Videos"),
        "videos":           os.path.join(os.environ.get("USERPROFILE", ""), "Videos"),
        "musique":          os.path.join(os.environ.get("USERPROFILE", ""), "Music"),
        "music":            os.path.join(os.environ.get("USERPROFILE", ""), "Music"),
        "corbeille":        "shell:RecycleBinFolder",
    }
    chemin_resolu = raccourcis.get(chemin.lower(), chemin)

    # Fallback FR si le dossier anglais n'existe pas
    if not os.path.exists(chemin_resolu):
        variantes = {
            "Downloads": "Téléchargements",
            "Pictures":  "Images",
            "Music":     "Musique",
        }
        for eng, fra in variantes.items():
            if eng in chemin_resolu:
                test_fra = chemin_resolu.replace(eng, fra)
                if os.path.exists(test_fra):
                    chemin_resolu = test_fra
                    break
    return chemin_resolu


def trouver_extension(ext: str) -> str:
    for categorie, extensions in EXTENSIONS.items():
        if ext.lower() in extensions:
            return categorie
    return "Autres"


# ── Opérations de base ─────────────────────────────────────────────────

def ouvrir_dossier(chemin: str) -> tuple[bool, str]:
    global dossier_courant
    chemin_resolu = resoudre_chemin(chemin)
    if not chemin_resolu or (
        not os.path.exists(chemin_resolu) and not chemin_resolu.startswith("shell:")
    ):
        return False, f"Dossier introuvable : {chemin_resolu}"
    dossier_courant = chemin_resolu
    if chemin_resolu.startswith("shell:"):
        subprocess.Popen(f'explorer "{chemin_resolu}"', shell=True)
    else:
        subprocess.Popen(["explorer", chemin_resolu])
    return True, chemin_resolu


def arranger_fenetres_dossiers():
    """Ouvre et dispose Documents, Téléchargements, Images et Vidéos en mosaïque 2×2."""
    dossiers = [
        ("documents",      0, 0),
        ("téléchargements", 1, 0),
        ("images",         0, 1),
        ("vidéos",         1, 1),
    ]
    # Dimensions écran via ctypes (pas besoin de pyautogui)
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    w, h = sw // 2, (sh - 40) // 2

    for nom, qx, qy in dossiers:
        ouvrir_dossier(nom)
        time.sleep(0.8)
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            user32.SetWindowPos(hwnd, 0, qx * w, qy * h, w, h, 0x0040)

    return "J'ai ouvert et disposé vos dossiers principaux en mosaïque."


def lister_dossier(chemin: str = None) -> tuple[dict | None, str | None]:
    cible = resoudre_chemin(chemin) if chemin else dossier_courant
    if not cible or not os.path.exists(cible):
        return None, "Aucun dossier ouvert ou chemin invalide."
    fichiers, dossiers = [], []
    for item in os.scandir(cible):
        if item.is_file():
            fichiers.append(item.name)
        elif item.is_dir():
            dossiers.append(item.name)
    return {"chemin": cible, "fichiers": fichiers, "dossiers": dossiers}, None


# ── Tri ───────────────────────────────────────────────────────────────

def trier_par_type(chemin: str = None) -> tuple[bool, str]:
    cible = resoudre_chemin(chemin) if chemin else dossier_courant
    if not cible or not os.path.exists(cible):
        return False, "Aucun dossier ouvert ou invalide."
    deplacements, erreurs, categories = 0, 0, {}
    for item in os.scandir(cible):
        if not item.is_file():
            continue
        ext       = Path(item.name).suffix
        categorie = trouver_extension(ext)
        dest_dir  = os.path.join(cible, categorie)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, item.name)
            if os.path.exists(dest_path):
                base = Path(item.name).stem
                dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext}")
            shutil.move(item.path, dest_path)
            deplacements += 1
            categories[categorie] = categories.get(categorie, 0) + 1
        except Exception as e:
            print(f"[FICHIER] Erreur déplacement {item.name} : {e}")
            erreurs += 1
    resume = ", ".join(f"{v} {k}" for k, v in categories.items())
    return True, f"{deplacements} fichiers triés : {resume}. {erreurs} erreur(s)."


def trier_par_date(chemin: str = None) -> tuple[bool, str]:
    cible = resoudre_chemin(chemin) if chemin else dossier_courant
    if not cible or not os.path.exists(cible):
        return False, "Aucun dossier ouvert ou invalide."
    deplacements, erreurs = 0, 0
    for item in os.scandir(cible):
        if not item.is_file():
            continue
        try:
            date     = datetime.fromtimestamp(item.stat().st_mtime)
            dest_dir = os.path.join(cible, str(date.year), date.strftime("%m - %B"))
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, item.name)
            if os.path.exists(dest_path):
                base = Path(item.name).stem
                ext  = Path(item.name).suffix
                dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{ext}")
            shutil.move(item.path, dest_path)
            deplacements += 1
        except Exception as e:
            print(f"[FICHIER] Erreur déplacement {item.name} : {e}")
            erreurs += 1
    return True, f"{deplacements} fichiers triés par date. {erreurs} erreur(s)."


# ── Opérations fichiers ────────────────────────────────────────────────

def creer_sous_dossier(nom: str, chemin: str = None) -> tuple[bool, str]:
    cible = resoudre_chemin(chemin) if chemin else dossier_courant
    if not cible:
        return False, "Aucun dossier ouvert."
    try:
        os.makedirs(os.path.join(cible, nom), exist_ok=True)
        return True, f"Dossier {nom} créé."
    except Exception as e:
        return False, f"Erreur création dossier : {e}"


def renommer_fichier(ancien_nom: str, nouveau_nom: str, chemin: str = None) -> tuple[bool, str]:
    cible = resoudre_chemin(chemin) if chemin else dossier_courant
    if not cible:
        return False, "Aucun dossier ouvert."
    try:
        os.rename(os.path.join(cible, ancien_nom), os.path.join(cible, nouveau_nom))
        return True, f"Fichier renommé en {nouveau_nom}."
    except Exception as e:
        return False, f"Erreur renommage : {e}"


def deplacer_fichier(nom_fichier: str, dossier_dest: str, chemin: str = None) -> tuple[bool, str]:
    cible = resoudre_chemin(chemin) if chemin else dossier_courant
    if not cible:
        return False, "Aucun dossier ouvert."
    try:
        dest = os.path.join(cible, dossier_dest)
        os.makedirs(dest, exist_ok=True)
        shutil.move(os.path.join(cible, nom_fichier), os.path.join(dest, nom_fichier))
        return True, f"{nom_fichier} déplacé dans {dossier_dest}."
    except Exception as e:
        return False, f"Erreur déplacement : {e}"


def chercher_fichier(nom: str, chemin: str = None) -> tuple[list, str | None]:
    cible = resoudre_chemin(chemin) if chemin else dossier_courant
    if not cible:
        return [], "Aucun dossier ouvert."
    resultats = []
    for root, _, files in os.walk(cible):
        for f in files:
            if nom.lower() in f.lower():
                resultats.append(os.path.join(root, f))
    return resultats, None
