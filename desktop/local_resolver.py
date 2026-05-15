"""
Résolution locale — réponses sans appel LLM.
Intercepte maths, conversions, traductions, minuteries, notes, liste de courses,
to-do, volume système, luminosité, arrêt PC, YouTube, salutations…
Appel unique : local_resolver.resoudre_tout(texte) → str | None
"""
import json
import math
import os
import random
import re
import string
import subprocess
import threading
import time
import webbrowser
import urllib.parse
from datetime import datetime
from typing import Callable, Optional

import requests

# ── Callback TTS injecté depuis VoicePipeline ──────────────────────────────────

_speak_fn: Optional[Callable[[str], None]] = None


def init(speak_fn: Callable[[str], None]) -> None:
    """Initialise la fonction TTS utilisée par les minuteries."""
    global _speak_fn
    _speak_fn = speak_fn


def _speak(text: str) -> None:
    if _speak_fn:
        _speak_fn(text)
    else:
        print(f"[local_resolver] TTS non init : {text}")


# ── Mémoire locale (jarvis_memoire.json) ──────────────────────────────────────

_MEMOIRE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_memoire.json")


def charger_memoire() -> dict:
    try:
        if os.path.exists(_MEMOIRE_PATH):
            with open(_MEMOIRE_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("memoire", {})
    except Exception:
        pass
    return {}


def ajouter_memoire(sujet: str, valeur: str) -> None:
    try:
        data: dict = {}
        if os.path.exists(_MEMOIRE_PATH):
            with open(_MEMOIRE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        mem = data.get("memoire", {})
        mem[sujet] = {"valeur": valeur, "date": datetime.now().strftime("%d/%m/%Y")}
        data["memoire"] = mem
        with open(_MEMOIRE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[local_resolver] Erreur mémoire : {e}")


# ── Listes (notes / courses / todos) ──────────────────────────────────────────

_LISTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_listes.json")


def _charger_listes() -> dict:
    try:
        if os.path.exists(_LISTES_PATH):
            with open(_LISTES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"notes": [], "courses": [], "todos": []}


def _sauvegarder_listes(data: dict) -> None:
    try:
        with open(_LISTES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[local_resolver] Erreur listes : {e}")


# ── Données statiques ──────────────────────────────────────────────────────────

_BLAGUES = [
    "Pourquoi les plongeurs plongent-ils toujours en arrière ? Parce que sinon ils tomberaient dans le bateau !",
    "Un homme entre dans une bibliothèque et demande : 'Avez-vous des livres sur la paranoïa ?' La bibliothécaire chuchote : 'Ils sont juste derrière vous.'",
    "Qu'est-ce qu'un canif ? Un petit fien.",
    "Pourquoi l'épouvantail a-t-il reçu un prix ? Parce qu'il était exceptionnel dans son domaine.",
    "Comment appelle-t-on un chat tombé dans un pot de peinture le jour de Noël ? Un chat-peint de Noël.",
    "Qu'est-ce qu'un crocodile qui surveille la cour d'école ? Un sac à dents.",
    "Pourquoi les mathématiciens confondent-ils Halloween et Noël ? Parce que Oct 31 = Dec 25.",
    "Un homme entre dans un bar... Aïe.",
    "Qu'est-ce qu'un agneau qui bégaie ? Du bé bé beurre.",
    "Comment on appelle un poisson sans yeux ? Un poisson.",
    "Qu'est-ce qu'un Tic qui tombe d'un arbre ? Un Tac.",
    "Pourquoi les girafes ont-elles un long cou ? Parce que leurs pieds sentent mauvais.",
    "Comment appelle-t-on un chat qui est tombé dans un pot de confiture ? Un chat confit.",
    "Qu'est-ce qu'un yaourt dans la forêt ? Un yaourt nature.",
    "Qu'est-ce qu'un cactus ? Un arbre bien défendu.",
    "Pourquoi les Belges mettent-ils leur portable dans la congélation ? Pour avoir des contacts froids.",
    "Qu'est-ce qu'un os dans un bain de boue ? Sherlock Bones.",
    "Qu'est-ce qu'un philosophe ? Un homme qui cherche dans une pièce noire un chapeau noir qui n'existe pas. Un théologien — il le trouve quand même.",
    "Comment appelle-t-on une ceinture en peau de crocodile ? Une ceinture qui fait le tour du ventre.",
    "Pourquoi le scarabée est-il si fort ? Parce qu'il soulève des bouses de vache.",
]

_CITATIONS = [
    "Le succès, c'est tomber sept fois et se relever huit. — Proverbe japonais",
    "La vie, c'est comme une bicyclette, il faut avancer pour ne pas perdre l'équilibre. — Albert Einstein",
    "Le seul moyen de faire du bon travail est d'aimer ce que vous faites. — Steve Jobs",
    "Celui qui déplace les montagnes commence par enlever les petites pierres. — Confucius",
    "N'attendez pas. Le moment ne sera jamais parfait. — Napoléon Hill",
    "La plus grande gloire n'est pas de ne jamais tomber, mais de se relever à chaque chute. — Nelson Mandela",
    "Vous ne pouvez pas aller en arrière et changer le début, mais vous pouvez commencer là où vous êtes et changer la fin. — C.S. Lewis",
    "Le pessimiste voit la difficulté dans chaque opportunité. L'optimiste voit l'opportunité dans chaque difficulté. — Winston Churchill",
    "Ce n'est pas la montagne que nous conquérons, mais nous-mêmes. — Edmund Hillary",
    "La créativité, c'est l'intelligence qui s'amuse. — Albert Einstein",
    "Chaque expert a un jour été un débutant. — Helen Hayes",
    "Votre temps est limité. Ne le gâchez pas en vivant la vie de quelqu'un d'autre. — Steve Jobs",
    "Tout ce que l'esprit peut concevoir et croire, il peut l'accomplir. — Napoleon Hill",
    "Le secret pour aller de l'avant, c'est de commencer. — Mark Twain",
    "Les personnes qui sont assez folles pour penser qu'elles peuvent changer le monde sont celles qui le font. — Apple",
]

_PHONETIQUE = {
    'a': 'Alpha', 'b': 'Bravo', 'c': 'Charlie', 'd': 'Delta', 'e': 'Echo',
    'f': 'Foxtrot', 'g': 'Golf', 'h': 'Hotel', 'i': 'India', 'j': 'Juliet',
    'k': 'Kilo', 'l': 'Lima', 'm': 'Mike', 'n': 'November', 'o': 'Oscar',
    'p': 'Papa', 'q': 'Quebec', 'r': 'Romeo', 's': 'Sierra', 't': 'Tango',
    'u': 'Uniform', 'v': 'Victor', 'w': 'Whiskey', 'x': 'X-ray', 'y': 'Yankee',
    'z': 'Zulu',
}

_CAPITALES = {
    "france": "Paris", "espagne": "Madrid", "italie": "Rome", "allemagne": "Berlin",
    "royaume-uni": "Londres", "angleterre": "Londres", "portugal": "Lisbonne",
    "pays-bas": "Amsterdam", "belgique": "Bruxelles", "suisse": "Berne",
    "autriche": "Vienne", "pologne": "Varsovie", "suede": "Stockholm",
    "norvege": "Oslo", "danemark": "Copenhague", "finlande": "Helsinki",
    "russie": "Moscou", "ukraine": "Kiev", "grece": "Athènes",
    "turquie": "Ankara", "maroc": "Rabat", "algerie": "Alger",
    "tunisie": "Tunis", "egypte": "Le Caire", "senegal": "Dakar",
    "etats-unis": "Washington", "canada": "Ottawa", "mexique": "Mexico",
    "bresil": "Brasília", "argentine": "Buenos Aires", "chili": "Santiago",
    "perou": "Lima", "colombie": "Bogotá", "chine": "Pékin",
    "japon": "Tokyo", "coree du sud": "Séoul", "inde": "New Delhi",
    "australie": "Canberra", "arabie saoudite": "Riyad", "israel": "Jérusalem",
    "iran": "Téhéran", "irak": "Bagdad", "nigeria": "Abuja", "kenya": "Nairobi",
    "ghana": "Accra", "qatar": "Doha", "indonesie": "Jakarta",
    "thaïlande": "Bangkok", "vietnam": "Hanoï", "philippines": "Manille",
    "malaisie": "Kuala Lumpur", "singapour": "Singapour",
}

_FUSEAUX = {
    "new york":      ("New York",     "America/New_York"),
    "los angeles":   ("Los Angeles",  "America/Los_Angeles"),
    "chicago":       ("Chicago",      "America/Chicago"),
    "montreal":      ("Montréal",     "America/Toronto"),
    "toronto":       ("Toronto",      "America/Toronto"),
    "london":        ("Londres",      "Europe/London"),
    "londres":       ("Londres",      "Europe/London"),
    "paris":         ("Paris",        "Europe/Paris"),
    "berlin":        ("Berlin",       "Europe/Berlin"),
    "madrid":        ("Madrid",       "Europe/Madrid"),
    "rome":          ("Rome",         "Europe/Rome"),
    "moscou":        ("Moscou",       "Europe/Moscow"),
    "dubai":         ("Dubaï",        "Asia/Dubai"),
    "inde":          ("Inde",         "Asia/Kolkata"),
    "mumbai":        ("Mumbai",       "Asia/Kolkata"),
    "delhi":         ("Delhi",        "Asia/Kolkata"),
    "pekin":         ("Pékin",        "Asia/Shanghai"),
    "shanghai":      ("Shanghai",     "Asia/Shanghai"),
    "tokyo":         ("Tokyo",        "Asia/Tokyo"),
    "seoul":         ("Séoul",        "Asia/Seoul"),
    "sydney":        ("Sydney",       "Australia/Sydney"),
    "melbourne":     ("Melbourne",    "Australia/Melbourne"),
    "sao paulo":     ("São Paulo",    "America/Sao_Paulo"),
    "buenos aires":  ("Buenos Aires", "America/Argentina/Buenos_Aires"),
    "mexico":        ("Mexico",       "America/Mexico_City"),
    "bangkok":       ("Bangkok",      "Asia/Bangkok"),
    "singapour":     ("Singapour",    "Asia/Singapore"),
    "hong kong":     ("Hong Kong",    "Asia/Hong_Kong"),
    "le caire":      ("Le Caire",     "Africa/Cairo"),
    "nairobi":       ("Nairobi",      "Africa/Nairobi"),
    "johannesburg":  ("Johannesburg", "Africa/Johannesburg"),
    "casablanca":    ("Casablanca",   "Africa/Casablanca"),
    "honolulu":      ("Honolulu",     "Pacific/Honolulu"),
}

# ── Minuteries actives ────────────────────────────────────────────────────────

_minuteries: dict[str, threading.Timer] = {}


def _parse_duree_secondes(texte: str) -> Optional[int]:
    t = texte.lower()
    total = 0
    h = re.search(r'(\d+)\s*(heure|h\b)', t)
    m = re.search(r'(\d+)\s*(minute|min\b)', t)
    s = re.search(r'(\d+)\s*(seconde|sec\b)', t)
    if h: total += int(h.group(1)) * 3600
    if m: total += int(m.group(1)) * 60
    if s: total += int(s.group(1))
    return total if total > 0 else None


# ── Volume système (pycaw — optionnel) ────────────────────────────────────────

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    _pycaw_ok = True
except ImportError:
    _pycaw_ok = False


def _volume_interface():
    if not _pycaw_ok:
        return None
    try:
        from ctypes import cast, POINTER
        devices = AudioUtilities.GetSpeakers()
        iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(iface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


# ── Luminosité (screen-brightness-control — optionnel) ───────────────────────

try:
    import screen_brightness_control as _sbc_mod
    _sbc_ok = True
except ImportError:
    _sbc_mod = None
    _sbc_ok  = False


# ══════════════════════════════════════════════════════════════════════════════
#  Résolveurs individuels
# ══════════════════════════════════════════════════════════════════════════════

def reponse_locale(texte: str) -> Optional[str]:
    """Salutations, remerciements, identité, mémoire — aucune API."""
    t = texte.lower().strip()

    # ── Salutations ───────────────────────────────────────────────────────────
    if any(m in t for m in ["bonjour", "salut", "hello", "bonsoir", "coucou",
                             "hey jarvis", "bien le bonjour", "good morning"]):
        h = int(time.strftime("%H"))
        moment = "Bonsoir" if h >= 18 else ("Bon après-midi" if h >= 12 else "Bonjour")
        return random.choice([
            f"{moment} Harry ! Je suis opérationnel et prêt à vous aider.",
            f"{moment} Monsieur ! Tous mes systèmes sont en ligne.",
            f"{moment} Harry ! Comment puis-je vous être utile aujourd'hui ?",
            f"Ah, {moment.lower()} Harry. Je vous attendais.",
        ])

    # ── État de JARVIS ────────────────────────────────────────────────────────
    if any(m in t for m in ["comment tu vas", "tu vas bien", "ça va toi", "comment ça va",
                             "en forme", "tu fonctionnes bien", "t'es en forme"]):
        return random.choice([
            "Je vais très bien merci, Harry ! Tous mes processeurs tournent à plein régime.",
            "Parfaitement opérationnel, Monsieur ! Merci de vous en préoccuper.",
            "En excellente forme, Harry. Mes algorithmes ronronnent comme une Lamborghini au ralenti.",
            "Très bien, je vous remercie ! Je reste à votre disposition avec plaisir.",
        ])

    # ── Remerciements ─────────────────────────────────────────────────────────
    # Exclure les demandes de traduction ("comment dit-on merci en anglais")
    if any(m in t for m in ["merci", "thank you", "c'est gentil", "merci beaucoup",
                             "merci jarvis", "bien joué", "bravo", "excellent",
                             "super boulot", "t'es le meilleur"]) and not any(
            ex in t for ex in ["comment dit-on", "traduis", "en anglais",
                                "en espagnol", "en allemand"]):
        return random.choice([
            "Avec plaisir, Harry. C'est exactement pour ça que j'existe.",
            "Je vous en prie, Monsieur. Votre satisfaction est ma priorité.",
            "Tout le plaisir est pour moi, Harry.",
            "À votre service, comme toujours.",
        ])

    # ── Au revoir ─────────────────────────────────────────────────────────────
    if any(m in t for m in ["au revoir", "bye", "à bientôt", "bonne nuit",
                             "bonne soirée", "bonne journée", "ciao", "tchao"]):
        return random.choice([
            "À bientôt Harry ! Je reste en veille, prêt à revenir.",
            "Bonne journée Monsieur ! Je serai là quand vous aurez besoin de moi.",
            "Au revoir Harry. JARVIS passe en mode veille.",
        ])

    # ── Identité ──────────────────────────────────────────────────────────────
    if any(m in t for m in ["qui es-tu", "ton nom", "t'appelle comment",
                             "quelle est ton identité", "c'est quoi jarvis"]):
        return ("Je suis JARVIS — Just A Rather Very Intelligent System. "
                "Votre assistant personnel développé par Morphoz.io.")

    if any(m in t for m in ["ton créateur", "qui t'a créé", "qui t'a fait",
                             "qui a fait jarvis", "qui est morphoz"]):
        return ("Mon créateur, c'est Morphoz.io. "
                "Une équipe passionnée qui m'a conçu pour être votre assistant personnel ultime. "
                "Retrouvez-nous sur morphoz.io.")

    # ── Enregistrement mémoire locale ─────────────────────────────────────────
    _triggers = ["enregistre que", "mémorise que", "note que", "rappelle-toi que"]
    for trig in _triggers:
        if trig in t:
            content = t.split(trig)[-1].strip()
            if not content:
                continue
            for sep in [" est ", " sont ", " s'appelle ", " se trouve ", " à "]:
                if sep in content:
                    parties = content.split(sep, 1)
                    sujet, valeur = parties[0].strip(), parties[1].strip()
                    if len(sujet) > 2 and len(valeur) > 1:
                        ajouter_memoire(sujet, valeur)
                        sujet_poli = sujet.replace("mon ", "votre ").replace("ma ", "votre ")
                        return f"C'est fait Harry, j'ai enregistré que {sujet_poli}{sep.strip()} {valeur}."
            ajouter_memoire("note_rapide", content)
            return f"C'est noté Harry, j'ai mis cela en mémoire : {content}."

    # ── Rappel mémoire locale ─────────────────────────────────────────────────
    if any(m in t for m in ["comment s'appelle", "où se trouve", "où est", "quelle est ma"]):
        for cle, data in charger_memoire().items():
            cle_clean = cle.replace("_", " ")
            if any(mot in t for mot in cle_clean.split() if len(mot) > 3) or cle_clean in t:
                cle_polie = cle_clean.replace("mon ", "votre ").replace("ma ", "votre ")
                return f"D'après mes dossiers, votre {cle_polie} est {data['valeur']}, Harry."

    return None


def resoudre_math_localement(texte: str) -> Optional[str]:
    """Calculs : '25 fois 4', 'racine de 144', '15 au carré'…"""
    t = texte.lower().replace("?", "").strip()

    # Doit ressembler à une question de calcul
    if not any(k in t for k in ["combien", "calcule", "résous", "résultat", "fois", "divisé",
                                  "plus", "moins", "racine", "carré", "puissance"]):
        return None

    for p in ["combien font", "combien fait", "calcule", "résous", "quel est le résultat de"]:
        if t.startswith(p):
            t = t[len(p):].strip()

    t = (t.replace("fois", "*").replace("multiplier par", "*")
          .replace("divisé par", "/")
          .replace(" plus ", "+").replace(" moins ", "-")
          .replace("puissance", "**").replace("au carré", "**2"))

    if "racine" in t:
        m = re.search(r'racine\s+(?:carrée\s+de\s+)?(\d+)', t)
        if m:
            t = f"sqrt({m.group(1)})"

    expr = re.sub(r'[^0-9+\-*/.**() sqrt]', '', t).strip()
    if not expr or not any(c.isdigit() for c in expr):
        return None
    if not any(op in expr for op in ['+', '-', '*', '/', '**', 'sqrt']):
        return None

    try:
        safe = {"sqrt": math.sqrt, "pow": math.pow, "pi": math.pi, "e": math.e,
                "__builtins__": None}
        result = eval(expr, {"__builtins__": None}, safe)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 4)
        clean = (expr.replace("**2", " au carré").replace("sqrt", "racine de ")
                     .replace("(", "").replace(")", "")
                     .replace("*", " fois ").replace("/", " divisé par "))
        return f"Le résultat de {clean.strip()} est {result}, Monsieur."
    except Exception:
        return None


def resoudre_conversion_localement(texte: str) -> Optional[str]:
    """Conversions : km↔miles, °C↔°F, €↔$, kg↔lbs."""
    t = texte.lower().replace("?", "").strip()

    # km → miles
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:km|kilom[eè]tres?)', t)
    if m and any(k in t for k in ["mile", "mille"]):
        val = float(m.group(1).replace(",", "."))
        return f"{val} kilomètre{'s' if val > 1 else ''} font environ {round(val * 0.621371, 2)} miles, Monsieur."

    # miles → km
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:miles?|milles?)', t)
    if m and any(k in t for k in ["km", "kilom"]):
        val = float(m.group(1).replace(",", "."))
        return f"{val} mile{'s' if val > 1 else ''} font environ {round(val / 0.621371, 2)} kilomètres, Monsieur."

    # °C → °F
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:degrés?|celsius)', t)
    if m and "fahrenheit" in t:
        val = float(m.group(1).replace(",", "."))
        return f"{val}°C font {round((val * 9/5) + 32, 1)}°F, Monsieur."

    # °F → °C
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*fahrenheit', t)
    if m and "celsius" in t:
        val = float(m.group(1).replace(",", "."))
        return f"{val}°F font {round((val - 32) * 5/9, 1)}°C, Monsieur."

    # € → $
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*euros?', t)
    if m and "dollar" in t:
        val = float(m.group(1).replace(",", "."))
        return f"{val} euro{'s' if val > 1 else ''} font environ {round(val * 1.08, 2)} dollars, Monsieur."

    # $ → €
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*dollars?', t)
    if m and "euro" in t:
        val = float(m.group(1).replace(",", "."))
        return f"{val} dollar{'s' if val > 1 else ''} font environ {round(val / 1.08, 2)} euros, Monsieur."

    # kg → lbs
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilogrammes?)', t)
    if m and any(k in t for k in ["livre", "pound", "lbs"]):
        val = float(m.group(1).replace(",", "."))
        return f"{val} kg font environ {round(val * 2.20462, 2)} livres, Monsieur."

    # lbs → kg
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:livres?|pounds?|lbs)', t)
    if m and any(k in t for k in ["kg", "kilo"]):
        val = float(m.group(1).replace(",", "."))
        return f"{val} livre{'s' if val > 1 else ''} font environ {round(val / 2.20462, 2)} kg, Monsieur."

    return None


def resoudre_traduction_localement(texte: str) -> Optional[str]:
    """Traduction rapide de mots courants FR→EN/ES/DE."""
    t = texte.lower().strip()
    if not any(p in t for p in ["comment dit-on", "traduis", "en anglais",
                                  "en espagnol", "en allemand"]):
        return None

    _dict: dict[str, dict[str, str]] = {
        "bonjour":        {"en": "hello",       "es": "hola",       "de": "hallo"},
        "merci":          {"en": "thank you",    "es": "gracias",    "de": "danke"},
        "au revoir":      {"en": "goodbye",      "es": "adiós",      "de": "auf wiedersehen"},
        "s'il vous plaît":{"en": "please",       "es": "por favor",  "de": "bitte"},
        "oui":            {"en": "yes",          "es": "sí",         "de": "ja"},
        "non":            {"en": "no",           "es": "no",         "de": "nein"},
        "ami":            {"en": "friend",       "es": "amigo",      "de": "freund"},
        "maison":         {"en": "house",        "es": "casa",       "de": "haus"},
        "ordinateur":     {"en": "computer",     "es": "ordenador",  "de": "computer"},
        "assistant":      {"en": "assistant",    "es": "asistente",  "de": "assistent"},
        "travail":        {"en": "work",         "es": "trabajo",    "de": "arbeit"},
        "voiture":        {"en": "car",          "es": "coche",      "de": "auto"},
        "chat":           {"en": "cat",          "es": "gato",       "de": "katze"},
        "chien":          {"en": "dog",          "es": "perro",      "de": "hund"},
        "eau":            {"en": "water",        "es": "agua",       "de": "wasser"},
        "pain":           {"en": "bread",        "es": "pan",        "de": "brot"},
    }

    cible = "en"
    if "espagnol" in t: cible = "es"
    elif "allemand" in t: cible = "de"

    mot = t
    for p in ["comment dit-on", "traduis le mot", "traduis", "en anglais",
              "en espagnol", "en allemand", "?"]:
        mot = mot.replace(p, "")
    mot = mot.replace('"', "").replace("'", "").strip()

    if mot in _dict:
        res  = _dict[mot][cible]
        lang = {"en": "anglais", "es": "espagnol", "de": "allemand"}[cible]
        return f"En {lang}, '{mot}' se dit '{res}'."

    return None


def resoudre_extras_locaux(texte: str) -> Optional[str]:  # noqa: C901 (fonction longue volontaire)
    """
    Minuteries, fuseaux, capitales, calcul d'âge, blagues, citations,
    pile/face, dé, MDP, notes, courses, to-do, volume, luminosité, PC.
    """
    t = texte.lower().replace("?", "").strip()

    # ══ MINUTERIE ═════════════════════════════════════════════════════════════
    if any(k in t for k in ["minuteur", "minuterie", "timer", "rappelle-moi dans",
                             "rappelle moi dans", "alarme dans", "lance un minuteur",
                             "active le minuteur", "préviens-moi dans"]):
        duree = _parse_duree_secondes(t)
        if duree:
            nom = f"timer_{len(_minuteries) + 1}"

            def _sonner(n=nom, d=duree):
                _minuteries.pop(n, None)
                _speak(random.choice([
                    "Monsieur, le compte à rebours est arrivé à échéance.",
                    "Harry, la minuterie est terminée. Tout est en ordre ?",
                    "Alerte : Le minuteur a atteint zéro, Harry.",
                    f"Fin du décompte, Harry. Je reste à votre disposition.",
                ]))

            timer = threading.Timer(duree, _sonner)
            timer.daemon = True
            timer.start()
            _minuteries[nom] = timer

            mins, secs = divmod(duree, 60)
            heures, mins = divmod(mins, 60)
            parts = []
            if heures: parts.append(f"{heures} heure{'s' if heures > 1 else ''}")
            if mins:   parts.append(f"{mins} minute{'s' if mins > 1 else ''}")
            if secs:   parts.append(f"{secs} seconde{'s' if secs > 1 else ''}")
            return f"Minuteur de {' et '.join(parts)} activé, Harry."
        return "Précisez la durée, par exemple : 'Mets un minuteur de 10 minutes'."

    if any(k in t for k in ["annule le minuteur", "annuler le minuteur", "stop minuteur",
                             "stop le minuteur", "arrête le minuteur", "stop le timer",
                             "arrête le timer"]):
        if _minuteries:
            for timer in _minuteries.values():
                timer.cancel()
            _minuteries.clear()
            return "Minuteur arrêté, Harry."
        return "Aucun minuteur actif en ce moment."

    # ══ FUSEAUX HORAIRES ══════════════════════════════════════════════════════
    # Détection souple : "heure" + une ville du dictionnaire dans la même phrase
    if "heure" in t and any(cle in t for cle in _FUSEAUX):
        for cle, (nom_ville, tz_str) in _FUSEAUX.items():
            if cle in t:
                # Tentative 1 : zoneinfo (nécessite tzdata sur Windows)
                try:
                    from zoneinfo import ZoneInfo
                    h = datetime.now(ZoneInfo(tz_str))
                    return f"Il est actuellement {h.strftime('%H:%M')} à {nom_ville}, Harry."
                except Exception:
                    pass
                # Tentative 2 : pytz
                try:
                    import pytz
                    h = datetime.now(pytz.timezone(tz_str))
                    return f"Il est actuellement {h.strftime('%H:%M')} à {nom_ville}, Harry."
                except Exception:
                    pass
                # Fallback : décalage UTC fixe (heure standard, sans DST)
                _UTC_OFFSETS: dict[str, int] = {
                    "America/New_York": -5, "America/Los_Angeles": -8,
                    "America/Chicago": -6, "America/Toronto": -5,
                    "Europe/London": 0, "Europe/Paris": 1, "Europe/Berlin": 1,
                    "Europe/Madrid": 1, "Europe/Rome": 1, "Europe/Moscow": 3,
                    "Asia/Dubai": 4, "Asia/Kolkata": 5, "Asia/Shanghai": 8,
                    "Asia/Tokyo": 9, "Asia/Seoul": 9, "Asia/Bangkok": 7,
                    "Asia/Singapore": 8, "Asia/Hong_Kong": 8,
                    "Australia/Sydney": 10, "Australia/Melbourne": 10,
                    "Africa/Cairo": 2, "Africa/Nairobi": 3,
                    "Africa/Johannesburg": 2, "Africa/Casablanca": 0,
                    "America/Sao_Paulo": -3,
                    "America/Argentina/Buenos_Aires": -3,
                    "America/Mexico_City": -6, "Pacific/Honolulu": -10,
                    "Pacific/Auckland": 12,
                }
                try:
                    from datetime import timezone, timedelta
                    offset = _UTC_OFFSETS.get(tz_str, 0)
                    h = datetime.now(timezone(timedelta(hours=offset)))
                    return (f"Il est actuellement {h.strftime('%H:%M')} à {nom_ville}, Harry. "
                            f"(heure standard UTC{'+' if offset >= 0 else ''}{offset})")
                except Exception:
                    pass
        return "Je ne reconnais pas cette ville dans ma base locale, Harry."

    # ══ CAPITALES ═════════════════════════════════════════════════════════════
    if any(k in t for k in ["capitale de", "capitale du", "capitale d'", "capital de"]):
        for pays, cap in _CAPITALES.items():
            if pays in t:
                return f"La capitale de {pays.title()} est {cap}, Harry."

    # ══ CALCUL D'ÂGE ══════════════════════════════════════════════════════════
    age_m = re.search(r'n[ée]\s+en\s+(\d{4})', t)
    if age_m:
        annee = int(age_m.group(1))
        return f"Si vous êtes né en {annee}, vous avez {datetime.now().year - annee} ans, Harry."

    if any(k in t for k in ["quel âge j'ai", "quel age j'ai", "calcule mon âge", "j'ai quel âge"]):
        return "Précisez votre année de naissance : 'né en 1990, quel âge j'ai ?'"

    # ══ COMPTE À REBOURS ══════════════════════════════════════════════════════
    if any(k in t for k in ["avant noël", "avant noel", "jours avant noël"]):
        today = datetime.now().date()
        noel  = datetime(today.year, 12, 25).date()
        if today > noel:
            noel = datetime(today.year + 1, 12, 25).date()
        j = (noel - today).days
        return f"Il reste {j} jour{'s' if j > 1 else ''} avant Noël, Harry !"

    if any(k in t for k in ["avant le nouvel an", "avant 2026", "avant 2027"]):
        today = datetime.now().date()
        an    = datetime(today.year + 1, 1, 1).date()
        j     = (an - today).days
        return f"Il reste {j} jours avant le Nouvel An, Harry !"

    # ══ BLAGUES ═══════════════════════════════════════════════════════════════
    if any(k in t for k in ["blague", "fais-moi rire", "fais moi rire", "raconte une blague",
                             "dis une blague", "une blague", "joke", "fais rire"]):
        return random.choice(_BLAGUES)

    # ══ CITATIONS ═════════════════════════════════════════════════════════════
    if any(k in t for k in ["citation", "inspire-moi", "inspire moi", "phrase motivante",
                             "motive-moi", "motive moi", "donne-moi une citation",
                             "parole sage"]):
        return random.choice(_CITATIONS)

    # ══ PILE OU FACE ══════════════════════════════════════════════════════════
    if any(k in t for k in ["pile ou face", "lance une pièce", "lance une piece",
                             "heads or tails"]):
        return f"J'ai lancé la pièce... C'est {random.choice(['Pile', 'Face'])} !"

    # ══ DÉ ════════════════════════════════════════════════════════════════════
    de_m = re.search(r'(?:lance|jette|tire|roule)\s+un\s+d[eé]', t)
    if de_m or "lance un dé" in t or "jette le dé" in t:
        nb_m = re.search(r'd[eé]\s+[aà]\s+(\d+)', t)
        nb = int(nb_m.group(1)) if nb_m else 6
        return f"J'ai lancé un dé à {nb} faces... Vous obtenez : {random.randint(1, nb)} !"

    # ══ NOMBRE ALÉATOIRE ══════════════════════════════════════════════════════
    if any(k in t for k in ["nombre aléatoire", "chiffre aléatoire", "génère un nombre",
                             "genere un nombre"]):
        rng_m = re.search(r'entre\s+(\d+)\s+et\s+(\d+)', t)
        if rng_m:
            a, b = int(rng_m.group(1)), int(rng_m.group(2))
            return f"Votre nombre aléatoire entre {a} et {b} : {random.randint(a, b)}"
        return f"Voici un nombre aléatoire : {random.randint(1, 100)}"

    # ══ GÉNÉRATEUR DE MOT DE PASSE ════════════════════════════════════════════
    if any(k in t for k in ["mot de passe", "password", "mdp sécurisé", "mdp securise",
                             "génère un mot de passe", "crée un mot de passe"]):
        longueur = 16
        lg_m = re.search(r'(\d+)\s*(?:caractères?|car)', t)
        if lg_m:
            longueur = min(max(int(lg_m.group(1)), 8), 64)
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        mdp   = ''.join(random.SystemRandom().choice(chars) for _ in range(longueur))
        return f"Votre mot de passe sécurisé ({longueur} caractères) : {mdp}"

    # ══ ALPHABET PHONÉTIQUE ═══════════════════════════════════════════════════
    if any(k in t for k in ["phonétique", "alphabet otan", "code otan"]):
        lettre_m = re.search(r'\blettre\s+([a-z])\b', t)
        if lettre_m:
            l = lettre_m.group(1)
            return f"En phonétique OTAN, {l.upper()} se dit {_PHONETIQUE.get(l, '?')}."
        lettres = ", ".join(_PHONETIQUE.values())
        return f"Alphabet phonétique OTAN : {lettres}."

    # ══ NOTES RAPIDES ═════════════════════════════════════════════════════════
    if any(k in t for k in ["note ça", "note ca", "prends note", "retiens ça",
                             "retiens ca", "mémorise ça", "memorise ca",
                             "mémorise ca", "écris ça", "ecris ca"]):
        contenu = t
        # Retirer les préfixes du plus long au plus court pour éviter les résidus
        for pref in sorted([
            "note ça :", "note ca :", "prends note de :", "prends note de",
            "retiens ça :", "retiens ca :", "mémorise ça :", "memorise ca :",
            "écris ça :", "ecris ca :", "note ça", "note ca",
            "prends note", "retiens ça", "retiens ca",
            "mémorise ça", "mémorise ca", "écris ça", "ecris ca",
        ], key=len, reverse=True):
            if contenu.startswith(pref):
                contenu = contenu[len(pref):].lstrip(" :").strip()
                break
        if contenu:
            listes = _charger_listes()
            listes["notes"].append(f"[{datetime.now().strftime('%d/%m %H:%M')}] {contenu}")
            _sauvegarder_listes(listes)
            return f"Note enregistrée, Harry : '{contenu}'"
        return "Que souhaitez-vous que je note ?"

    if any(k in t for k in ["mes notes", "lis mes notes", "affiche mes notes", "montre mes notes"]):
        listes = _charger_listes()
        if not listes["notes"]:
            return "Vous n'avez aucune note enregistrée, Harry."
        items = " — ".join(listes["notes"][-5:])
        return f"Vos {min(5, len(listes['notes']))} dernières notes : {items}"

    if any(k in t for k in ["efface mes notes", "supprime mes notes", "vide mes notes",
                             "clear mes notes"]):
        listes = _charger_listes()
        listes["notes"] = []
        _sauvegarder_listes(listes)
        return "Toutes vos notes ont été effacées, Harry."

    # ══ LISTE DE COURSES ══════════════════════════════════════════════════════
    if any(k in t for k in ["liste de courses", "mes courses", "liste d'achats"]):
        if any(k in t for k in ["ajoute", "rajoute", "mets"]):
            # Extraction robuste : on retire les mots-outils autour de l'article
            article = re.sub(
                r"\b(ajoute|rajoute|mets|à ma liste de courses|à mes courses|"
                r"liste de courses|mes courses|à ma liste d'achats|dans ma liste|"
                r"dans les courses|sur ma liste)\b",
                "", t
            ).strip()
            article = re.sub(r"\s+", " ", article).strip(" ,.:;")
            if article:
                listes = _charger_listes()
                listes["courses"].append(article)
                _sauvegarder_listes(listes)
                return f"'{article}' ajouté à votre liste de courses, Harry."
        if any(k in t for k in ["vide", "efface", "supprime", "clear"]):
            listes = _charger_listes()
            listes["courses"] = []
            _sauvegarder_listes(listes)
            return "Liste de courses vidée, Harry."
        listes = _charger_listes()
        if not listes["courses"]:
            return "Votre liste de courses est vide, Harry."
        items = " — ".join(listes["courses"])
        n = len(listes["courses"])
        return f"Liste de courses ({n} article{'s' if n > 1 else ''}) : {items}"

    # ══ TO-DO LIST ════════════════════════════════════════════════════════════
    if any(k in t for k in ["tâche", "tache", "to-do", "todo"]):
        if any(k in t for k in ["ajoute", "nouvelle", "crée", "ajouter"]):
            tache = t
            for pref in ["ajoute une tâche", "ajoute une tache", "nouvelle tâche",
                         "nouvelle tache", "à faire :", "a faire :",
                         "à faire", "a faire", "ajoute "]:
                tache = tache.replace(pref, "").strip()
            if tache:
                listes = _charger_listes()
                listes["todos"].append({
                    "tache": tache, "fait": False,
                    "date": datetime.now().strftime("%d/%m"),
                })
                _sauvegarder_listes(listes)
                return f"Tâche ajoutée : '{tache}', Harry."
        if any(k in t for k in ["mes tâches", "mes taches", "ma to-do", "liste de tâches",
                                  "qu'est-ce que j'ai à faire"]):
            listes = _charger_listes()
            todos = [td for td in listes["todos"] if not td.get("fait")]
            if not todos:
                return "Votre liste de tâches est vide, Harry. Bravo !"
            items = " — ".join(f"[{td['date']}] {td['tache']}" for td in todos[-8:])
            return f"Vos tâches à faire ({len(todos)}) : {items}"
        if any(k in t for k in ["efface mes tâches", "vide ma to-do", "supprime mes tâches"]):
            listes = _charger_listes()
            listes["todos"] = []
            _sauvegarder_listes(listes)
            return "Liste de tâches vidée, Harry."

    # ══ VOLUME SYSTÈME (pycaw) ════════════════════════════════════════════════
    if any(k in t for k in ["volume", "son"]) and any(
            k in t for k in ["monte", "baisse", "coupe", "mute", "unmute",
                              "remet le son", "réactive", "%", "pourcent",
                              "mets le volume", "mets le son"]):
        vol = _volume_interface()
        if not vol:
            return "Contrôle du volume indisponible. Installez pycaw : pip install pycaw."
        if any(k in t for k in ["coupe", "mute", "sourdine", "silence total"]):
            vol.SetMute(1, None)
            return "Son coupé, Harry."
        if any(k in t for k in ["remet le son", "unmute", "réactive le son", "rétablis le son"]):
            vol.SetMute(0, None)
            return "Son réactivé, Harry."
        vol_m = re.search(r'(\d+)\s*(?:%|pourcent)', t)
        if vol_m:
            pct = max(0, min(100, int(vol_m.group(1))))
            vol.SetMasterVolumeLevelScalar(pct / 100.0, None)
            return f"Volume réglé à {pct}%, Harry."
        if any(k in t for k in ["monte", "augmente", "plus fort", "hausse"]):
            cur   = vol.GetMasterVolumeLevelScalar()
            new_v = min(1.0, cur + 0.1)
            vol.SetMasterVolumeLevelScalar(new_v, None)
            return f"Volume augmenté à {int(new_v * 100)}%, Harry."
        if any(k in t for k in ["baisse", "diminue", "moins fort", "réduis"]):
            cur   = vol.GetMasterVolumeLevelScalar()
            new_v = max(0.0, cur - 0.1)
            vol.SetMasterVolumeLevelScalar(new_v, None)
            return f"Volume réduit à {int(new_v * 100)}%, Harry."

    # ══ LUMINOSITÉ ════════════════════════════════════════════════════════════
    if any(k in t for k in ["luminosité", "luminosite", "écran plus clair",
                             "écran plus sombre", "brillo"]):
        if not (_sbc_ok and _sbc_mod):
            return ("Module de luminosité non installé. "
                    "Lancez : pip install screen-brightness-control")
        try:
            lum_m = re.search(r'(\d+)\s*(?:%|pourcent)', t)
            if lum_m:
                pct = max(0, min(100, int(lum_m.group(1))))
                _sbc_mod.set_brightness(pct)
                return f"Luminosité réglée à {pct}%, Harry."
            if any(k in t for k in ["monte", "augmente", "plus clair", "max"]):
                cur = _sbc_mod.get_brightness(display=0)
                if isinstance(cur, list): cur = cur[0]
                new_b = min(100, cur + 15)
                _sbc_mod.set_brightness(new_b)
                return f"Luminosité augmentée à {new_b}%, Harry."
            if any(k in t for k in ["baisse", "diminue", "plus sombre", "min"]):
                cur = _sbc_mod.get_brightness(display=0)
                if isinstance(cur, list): cur = cur[0]
                new_b = max(0, cur - 15)
                _sbc_mod.set_brightness(new_b)
                return f"Luminosité réduite à {new_b}%, Harry."
        except Exception as e:
            return f"Impossible de régler la luminosité : {e}"

    # ══ VEILLE / ARRÊT / REDÉMARRAGE PC ══════════════════════════════════════
    if any(k in t for k in ["mets le pc en veille", "mode veille", "suspends le pc",
                             "sleep le pc"]):
        delai = _parse_duree_secondes(t) or 0
        if delai > 0:
            subprocess.Popen(f'shutdown /h /t {delai}', shell=True)
            return f"Le PC passera en veille dans {delai // 60} minute{'s' if delai >= 120 else ''}, Harry."
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return "Mise en veille du PC, Harry. À bientôt !"

    if any(k in t for k in ["éteins le pc", "eteins le pc", "arrête le pc",
                             "arrete le pc", "shutdown le pc"]):
        delai = _parse_duree_secondes(t) or 0
        if delai > 0:
            subprocess.Popen(f'shutdown /s /t {delai}', shell=True)
            return f"Le PC s'éteindra dans {delai // 60} minute{'s' if delai >= 120 else ''}, Harry."
        return "Pour l'arrêt immédiat, dites : 'confirme l'arrêt du PC'."

    if any(k in t for k in ["confirme l'arrêt", "confirme larret", "éteins maintenant"]):
        subprocess.Popen("shutdown /s /t 5", shell=True)
        return "Extinction du PC dans 5 secondes, Harry. Bonne journée !"

    if any(k in t for k in ["redémarre le pc", "redémarre", "restart", "reboot"]):
        subprocess.Popen("shutdown /r /t 5", shell=True)
        return "Redémarrage du PC dans 5 secondes, Harry."

    # ══ YOUTUBE ═══════════════════════════════════════════════════════════════
    if "youtube" in t:
        return _chercher_youtube(t)

    return None


def _chercher_youtube(texte: str) -> str:
    """Ouvre YouTube avec une recherche — utilise l'API si YOUTUBE_API_KEY configurée."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
    api_key = os.getenv("YOUTUBE_API_KEY", "")

    recherche = texte
    for mot in ["mets", "joue", "lance", "la video", "la vidéo", "sur youtube",
                "youtube", "jarvis", "cherche", "ouvre"]:
        recherche = recherche.replace(mot, "")
    recherche = recherche.strip()

    if not recherche:
        webbrowser.open("https://www.youtube.com")
        return "J'ouvre YouTube, Harry."

    if api_key and api_key not in ("", "VOTRE_CLE_ICI"):
        try:
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": recherche, "type": "video",
                        "maxResults": 1, "key": api_key},
                timeout=5,
            )
            vid = r.json()["items"][0]["id"]["videoId"]
            webbrowser.open(f"https://www.youtube.com/watch?v={vid}")
            return f"Je lance '{recherche}' sur YouTube, Harry."
        except Exception as e:
            print(f"[youtube] Erreur API : {e}")

    # Fallback sans clé : recherche directe
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(recherche)}"
    webbrowser.open(url)
    return f"Je recherche '{recherche}' sur YouTube, Harry."


# ══════════════════════════════════════════════════════════════════════════════
#  Point d'entrée unique
# ══════════════════════════════════════════════════════════════════════════════

def resoudre_tout(texte: str) -> Optional[str]:
    """
    Essaie tous les résolveurs locaux dans l'ordre.
    Retourne None si aucun ne correspond → le caller doit passer au LLM.
    """
    for resolveur in [
        reponse_locale,
        resoudre_math_localement,
        resoudre_conversion_localement,
        resoudre_traduction_localement,
        resoudre_extras_locaux,
    ]:
        try:
            result = resolveur(texte)
            if result:
                return result
        except Exception as e:
            print(f"[local_resolver] Erreur dans {resolveur.__name__} : {e}")
    return None
